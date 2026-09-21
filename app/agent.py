import time
from collections.abc import Callable

from app.memory import ConversationStore
from app.providers import AgentError
from app.tools.placement_tools import PlacementTools


MAX_STEPS = 8


SYSTEM = """You are the Placement Assistant for an engineering college's placement cell.
You are talking to the student with roll number {student_id}. Act only for this student.
Use the tools for every fact about drives, eligibility, applications and slots; never guess.
Eligibility is decided by check_eligibility, not by you. Keep replies short and concrete."""


class Agent:
    """A small agent: one student, one conversation, the placement tools."""

    def __init__(
        self,
        provider,
        tools: PlacementTools,
        student_id: str,
        memory: ConversationStore | None = None,
        thread_id: str | None = None,
        on_step: Callable[[dict], None] | None = None,
    ):
        self.provider = provider
        self.tools = tools
        self.system = SYSTEM.format(student_id=student_id)
        self.memory = memory
        self.thread_id = thread_id
        self.on_step = on_step

        self.contents: list[dict] = []
        self.trace: list[dict] = []

        # Part 3.3:
        # Load previous conversation from SQLite.
        if self.memory is not None and self.thread_id is not None:
            history = self.memory.load_history(self.thread_id)

            self.contents = [
                {
                    "role": message["role"],
                    "text": message["text"],
                }
                for message in history
            ]

    def _log(self, entry: dict) -> None:
        """Add one entry to the trace and tell on_step about it."""
        self.trace.append(entry)

        if self.on_step:
            self.on_step(entry)

    # ------------------------------------------------------------------
    # Part 2.1
    # ------------------------------------------------------------------

    def run_tool(self, name: str, args: dict) -> dict:
        """Call one tool with self.tools.call(name, args). Never raise."""

        try:
            return self.tools.call(name, args)

        except NotImplementedError:
            return {
                "error": "not_implemented",
                "hint": f"Tool '{name}' is not implemented yet.",
            }

        except Exception as e:
            return {
                "error": "tool_failed",
                "hint": f"Tool '{name}' failed with {type(e).__name__}.",
            }

    # ------------------------------------------------------------------
    # Part 2.2 + Part 3.3
    # ------------------------------------------------------------------

    def ask(self, text: str) -> str:
        """One user turn: loop model calls and tool calls until the model answers."""

        # --------------------------------------------------------------
        # 1. Save user message
        # --------------------------------------------------------------

        self.contents.append(
            {
                "role": "user",
                "text": text,
            }
        )

        if self.memory is not None and self.thread_id is not None:
            self.memory.append_message(
                self.thread_id,
                "user",
                text,
            )

        # --------------------------------------------------------------
        # 2. Start a run if memory is enabled
        # --------------------------------------------------------------

        run_id = None

        if self.memory is not None and self.thread_id is not None:
            model_name = getattr(
                self.provider,
                "model_name",
                getattr(self.provider, "model", "unknown"),
            )

            run_id = self.memory.start_run(
                self.thread_id,
                model_name,
            )

        step = 0

        try:

            # ----------------------------------------------------------
            # 3. Keep asking the model until it gives a final answer
            # ----------------------------------------------------------

            while step < MAX_STEPS:

                # ------------------------------------------------------
                # Model step
                # ------------------------------------------------------

                turn = self.provider.generate(
                    self.system,
                    self.contents,
                    list(self.tools.functions().values()),
                )

                step += 1

                tokens_in = getattr(turn, "tokens_in", 0) or 0
                tokens_out = getattr(turn, "tokens_out", 0) or 0

                self._log(
                    {
                        "step": step,
                        "kind": "model",
                        "tokens_in": tokens_in,
                        "tokens_out": tokens_out,
                    }
                )

                # Save model step to persistent memory.
                if run_id is not None:
                    self.memory.record_model_step(
                        run_id,
                        step,
                        tokens_in,
                        tokens_out,
                    )

                # ------------------------------------------------------
                # 4. If model did not request a tool, return its answer
                # ------------------------------------------------------

                if not turn.tool_calls:

                    reply = turn.text or ""

                    self.contents.append(
                        {
                            "role": "model",
                            "text": reply,
                            "raw": turn.raw,
                        }
                    )

                    # Save final model response.
                    if self.memory is not None and self.thread_id is not None:
                        self.memory.append_message(
                            self.thread_id,
                            "model",
                            reply,
                        )

                    # Mark run successful.
                    if run_id is not None:
                        self.memory.finish_run(
                            run_id,
                            "succeeded",
                        )

                    return reply

                # ------------------------------------------------------
                # 5. Model requested one or more tools
                # ------------------------------------------------------

                self.contents.append(
                    {
                        "role": "model",
                        "text": turn.text,
                        "raw": turn.raw,
                        "tool_calls": [
                            {
                                "name": call.name,
                                "args": call.args,
                            }
                            for call in turn.tool_calls
                        ],
                    }
                )

                # ------------------------------------------------------
                # 6. Execute every tool call in order
                # ------------------------------------------------------

                for call in turn.tool_calls:

                    # A tool call is also a step.
                    if step >= MAX_STEPS:
                        raise AgentError(
                            "step_limit",
                            f"Agent exceeded the maximum of {MAX_STEPS} steps.",
                        )

                    start = time.perf_counter()

                    result = self.run_tool(
                        call.name,
                        call.args,
                    )

                    elapsed_ms = int(
                        (time.perf_counter() - start) * 1000
                    )

                    step += 1

                    ok = "error" not in result

                    # --------------------------------------------------
                    # Log tool step
                    # --------------------------------------------------

                    self._log(
                        {
                            "step": step,
                            "kind": "tool",
                            "tool": call.name,
                            "args": call.args,
                            "result": result,
                            "ok": ok,
                            "ms": elapsed_ms,
                        }
                    )

                    # Save tool step to persistent memory.
                    if run_id is not None:
                        self.memory.record_tool_call(
                            run_id,
                            step,
                            call.name,
                            call.args,
                            result,
                            ok,
                            elapsed_ms,
                        )

                    # --------------------------------------------------
                    # Give tool result back to the model
                    # --------------------------------------------------

                    self.contents.append(
                        {
                            "role": "tool",
                            "name": call.name,
                            "result": result,
                        }
                    )

            # ----------------------------------------------------------
            # Maximum number of steps reached
            # ----------------------------------------------------------

            raise AgentError(
                "step_limit",
                f"Agent exceeded the maximum of {MAX_STEPS} steps.",
            )

        except AgentError as e:

            # If the agent crashes after some work, preserve everything
            # already recorded and mark the run as failed.
            if run_id is not None:
                self.memory.finish_run(
                    run_id,
                    "failed",
                    e.code,
                )

            raise