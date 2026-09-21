from collections.abc import Callable

from pydantic import BaseModel, Field, ValidationError, model_validator  # noqa: F401


class FailedRule(BaseModel):
    rule_id: int
    rule: str
    actual: str | float


class EligibilityVerdict(BaseModel):
    student_id: str = Field(pattern=r"^\d{2}[A-Z]{2}\d{3}$")
    drive_id: int
    eligible: bool
    failed_rules: list[FailedRule]
    summary: str = Field(min_length=1, max_length=280)

    @model_validator(mode="after")
    def check_eligibility_consistency(self):
        if self.eligible and self.failed_rules:
            raise ValueError(
                "eligible=True contradicts the presence of failed_rules"
            )

        if not self.eligible and not self.failed_rules:
            raise ValueError(
                "eligible=False contradicts the absence of failed_rules"
            )

        return self


class VerdictInvalid(Exception):
    def __init__(self, attempts: int, last_errors: list):
        super().__init__(f"no valid verdict after {attempts} attempts")
        self.attempts = attempts
        self.last_errors = last_errors


Generate = Callable[[list[str]], str]


def _strip_fences(text: str) -> str:
    t = text.strip()

    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        t = t.rsplit("```", 1)[0]

    return t.strip()


def structured_verdict(
    generate: Generate,
    prompt: str,
    max_retries: int = 2
) -> EligibilityVerdict:
    """Ask the model for an EligibilityVerdict; feed validation errors back;
    give up after max_retries.

    The model starts with the given prompt. Its response is parsed as JSON
    using EligibilityVerdict. If validation fails, the raw response and
    validation feedback are added to the conversation so the model can retry.

    At most 1 + max_retries calls are made.
    """

    messages = [prompt]
    attempts = 0
    last_errors = []

    while attempts < 1 + max_retries:
        attempts += 1

        raw = generate(messages)

        try:
            verdict = EligibilityVerdict.model_validate_json(
                _strip_fences(raw)
            )

            return verdict

        except ValidationError as e:
            last_errors = e.errors()

            messages.append(raw)

            messages.append(
                "Your previous response failed validation. "
                "Fix the validation errors and return valid JSON. "
                f"Errors: {e.errors()}"
            )

    raise VerdictInvalid(attempts, last_errors)