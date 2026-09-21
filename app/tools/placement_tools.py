import operator
from datetime import datetime, timezone

from app.domain import AlreadyApplied, Rule, Student
from app.data import InMemoryPlacementRepo
from app.tools.dispatch import dispatch

OPS = {
    ">=": operator.ge,
    "<=": operator.le,
    "==": operator.eq,
    "in": lambda actual, allowed: actual in allowed.split(","),
}


def _passes(rule: Rule, student_value) -> bool:
    return OPS[rule.op](student_value, rule.typed_value())


def _unknown_student(roll_no: str) -> dict:
    return {
        "error": "unknown_student",
        "hint": f"No student with roll number {roll_no!r}. "
                 f"Ask the user for their roll number, e.g. 22CS045."
    }


def _unknown_drive(drive_id: int) -> dict:
    return {
        "error": "unknown_drive",
        "hint": f"No drive with id {drive_id}. "
                 f"Call list_open_drives to get valid ids."
    }


class PlacementTools:
    """Every method named in TOOL_NAMES is exposed to the model. Its docstring IS the prompt.

    Two tools are complete samples: check_eligibility (read-only) and apply_to_drive (side effect).
    Copy their patterns for the tools marked TODO.
    """

    READ_ONLY = (
        "list_open_drives",
        "get_student",
        "check_eligibility"
    )

    SIDE_EFFECTS = (
        "apply_to_drive",
        "book_interview_slot",
        "notify_student"
    )

    TOOL_NAMES = READ_ONLY + SIDE_EFFECTS

    def __init__(
        self,
        repo: InMemoryPlacementRepo,
        notifier,
        clock=lambda: datetime.now(timezone.utc)
    ):
        self.repo = repo
        self.notifier = notifier
        self.clock = clock

    def functions(self) -> dict:
        return {
            name: getattr(self, name)
            for name in self.TOOL_NAMES
        }

    def call(self, name: str, args: dict) -> dict:
        return dispatch(self.functions(), name, args)

    # ==================================================================
    # SAMPLE 1 (given): read-only

    def _evaluate(self, s: Student, drive_id: int) -> list[dict]:
        # The business rule lives in data (placement.eligibility_rule),
        # not in the prompt or an if.
        failed = []

        for rule in self.repo.rules_for_drive(drive_id):
            actual = getattr(s, rule.field)

            if not _passes(rule, actual):
                failed.append({
                    "rule_id": rule.id,
                    "rule": str(rule),
                    "actual": actual
                })

        return failed

    def check_eligibility(
        self,
        student_id: str,
        drive_id: int
    ) -> dict:
        """Decide whether ONE student may apply to ONE drive, using the drive's eligibility rules.

        Use before apply_to_drive, or when the user asks "can I apply", "am I eligible for
        <company>", or "why can't I apply". Do NOT use to find drives; use list_open_drives.
        Read-only: changes nothing.

        Args:
            student_id: Roll number, e.g. "22CS045".
            drive_id: Integer id returned by list_open_drives. Never a company name.

        Returns:
            {"student_id", "drive_id", "eligible", "failed_rules": [{"rule_id", "rule", "actual"}]}.
            Explain every failed rule to the user; do not invent rules that are not listed.
        """

        # Failures are returned, never raised.
        s = self.repo.get_student(student_id)

        if s is None:
            return _unknown_student(student_id)

        if self.repo.get_drive(drive_id) is None:
            return _unknown_drive(drive_id)

        # Every failed rule, not just the first.
        failed = self._evaluate(s, drive_id)

        return {
            "student_id": s.roll_no,
            "drive_id": drive_id,
            "eligible": not failed,
            "failed_rules": failed
        }

    # ==================================================================
    # SAMPLE 2 (given): side effect

    def apply_to_drive(
        self,
        student_id: str,
        drive_id: int
    ) -> dict:
        """Submit a placement application for ONE student to ONE drive.

        Side effect: creates an application record the placement cell will act on. Call it only
        when the user clearly asks to apply or register ("apply me", "sign me up"), never to
        check or explore. Eligibility is re-checked here, but call check_eligibility first so
        you can explain the result.

        Args:
            student_id: Roll number, e.g. "22CS045".
            drive_id: Integer id returned by list_open_drives.

        Returns:
            {"application_id", "student_id", "drive_id", "status": "applied",
             "available_slots": [{"slot_id", "starts_at"}]}. Offer the slots to the user;
            book one only when they choose.
        """

        # Side effects check in a fixed order and stop at the first failure.
        s = self.repo.get_student(student_id)

        if s is None:
            return _unknown_student(student_id)

        d = self.repo.get_drive(drive_id)

        if d is None:
            return _unknown_drive(drive_id)

        if d.status != "open" or d.deadline <= self.clock():
            return {
                "error": "drive_closed",
                "hint": f"{d.company} is not accepting applications. "
                        f"Call list_open_drives for open ones."
            }

        # Re-check eligibility.
        failed = self._evaluate(s, drive_id)

        if failed:
            return {
                "error": "not_eligible",
                "failed_rules": failed,
                "hint": "Explain the failed rules to the user. Do not retry."
            }

        try:
            application_id = self.repo.create_application(
                s.id,
                drive_id
            )

        except AlreadyApplied:
            return {
                "error": "already_applied",
                "hint": "The student has already applied to this drive. "
                        "Tell the user; do not retry."
            }

        # Return available interview slots.
        slots = self.repo.free_slots(drive_id)

        return {
            "application_id": application_id,
            "student_id": s.roll_no,
            "drive_id": drive_id,
            "status": "applied",
            "available_slots": [
                {
                    "slot_id": sl.id,
                    "starts_at": sl.starts_at.isoformat()
                }
                for sl in slots
            ]
        }

    # ==================================================================
    # YOUR TOOLS

    # TODO 1 — get_student

    def get_student(self, student_id: str) -> dict:
        """Read-only: Get the basic record of ONE student.

        Use when the user asks about a student's record, such as their name, branch,
        CGPA, backlogs, or graduation year. Do NOT use to decide eligibility;
        use check_eligibility for that.

        Args:
            student_id: Student roll number, e.g. "22CS045".

        Returns:
            {"student_id", "name", "branch", "cgpa", "backlogs", "grad_year"}.
            If the student does not exist, return an unknown_student error.
        """

        s = self.repo.get_student(student_id)

        if s is None:
            return _unknown_student(student_id)

        return {
            "student_id": s.roll_no,
            "name": s.name,
            "branch": s.branch,
            "cgpa": s.cgpa,
            "backlogs": s.backlogs,
            "grad_year": s.grad_year
        }

    # ==================================================================
    # TODO 2 — list_open_drives

    def list_open_drives(
        self,
        branch: str | None = None,
        grad_year: int | None = None
    ) -> dict:
        """Read-only: List currently open placement drives.

        Use when the user asks which companies or placement drives are open.
        Optional branch and graduation-year filters can narrow the results.
        Do NOT use this to check whether a particular student is eligible;
        use check_eligibility for that.

        Args:
            branch: Optional branch filter, e.g. "CSE", "IT", or "ECE".
            grad_year: Optional graduation year, e.g. 2026.

        Returns:
            {"drives": [{"drive_id", "company", "role", "ctc_lpa", "deadline"}]}.
            Drives are returned with the soonest deadline first.
        """

        drives = self.repo.list_open_drives(self.clock())

        result = []

        for d in drives:
            rules = self.repo.rules_for_drive(d.id)

            # Check branch filter
            if branch is not None:
                branch_ok = True

                for rule in rules:
                    if rule.field == "branch":
                        branch_ok = _passes(rule, branch)
                        break

                if not branch_ok:
                    continue

            # Check graduation year filter
            if grad_year is not None:
                year_ok = True

                for rule in rules:
                    if rule.field == "grad_year":
                        year_ok = _passes(rule, grad_year)
                        break

                if not year_ok:
                    continue

            result.append({
                "drive_id": d.id,
                "company": d.company,
                "role": d.role,
                "ctc_lpa": d.ctc_lpa,
                "deadline": d.deadline.strftime("%Y-%m-%d")
            })

        return {
            "drives": result
        }

    # ==================================================================
    # TODO 3 — book_interview_slot

    def book_interview_slot(
        self,
        student_id: str,
        slot_id: int
    ) -> dict:
        """Book ONE interview slot for ONE student.

        Side effect: reserves an interview slot. Call only when the user clearly
        asks to book a specific slot they have chosen. Do NOT use to find slots.

        Args:
            student_id: Student roll number, e.g. "22CS045".
            slot_id: Integer slot id returned by apply_to_drive.

        Returns:
            {"slot_id", "drive_id", "starts_at", "status": "booked"}.
        """

        # 1. Check student
        s = self.repo.get_student(student_id)

        if s is None:
            return _unknown_student(student_id)

        # 2. Check slot
        slot = self.repo.get_slot(slot_id)

        if slot is None:
            return {
                "error": "unknown_slot",
                "hint": f"No interview slot with id {slot_id}."
            }

        # 3. Check whether student applied to the drive
        if not self.repo.has_application(
            s.id,
            slot.drive_id
        ):
            return {
                "error": "no_application",
                "hint": "The student must apply to this drive "
                        "before booking an interview slot."
            }

        # 4. Try to claim the slot
        if not self.repo.claim_slot(
            slot_id,
            s.id
        ):
            slots = self.repo.free_slots(slot.drive_id)

            return {
                "error": "slot_taken",
                "hint": "That slot was just taken. "
                        "Ask the user to choose another available slot.",
                "available_slots": [
                    {
                        "slot_id": sl.id,
                        "starts_at": sl.starts_at.isoformat()
                    }
                    for sl in slots
                ]
            }

        # 5. Successfully booked
        return {
            "slot_id": slot.id,
            "drive_id": slot.drive_id,
            "starts_at": slot.starts_at.isoformat(),
            "status": "booked"
        }

     # ==================================================================
    # TODO 4 (lab 1) — notify_student

    def notify_student(
        self,
        student_id: str,
        message: str
    ) -> dict:
        """Side effect: Queue one notification for a registered student.

        Use only when the user clearly asks to notify or send a message to the
        student. Do NOT use this tool to check student details or eligibility.

        Parameters:
        - student_id: the student's roll number, for example "22CS045".
        - message: the notification text, which must be between 1 and 160 characters.

        This tool queues exactly one notification and returns its notification id
        and queued status.
        """

        # 1. Check that the student exists
        s = self.repo.get_student(student_id)

        if s is None:
            return _unknown_student(student_id)

        # 2. Validate the message
        if not message or len(message) > 160:
            return {
                "error": "invalid_message",
                "hint": "Message must be between 1 and 160 characters."
            }

        # 3. Send exactly one notification
        notification_id = self.notifier.send(
            student_id,
            message
        )

        return {
            "notification_id": notification_id,
            "status": "queued"
        }