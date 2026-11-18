import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

from tools import (
    check_dns,
    check_https,
    check_nginx,
    check_loandocx,
    restart_loandocx,
    check_nginx_error_log,
    check_loandocx_logs,
    check_loandocx_port,
    check_nginx_upstream,
    check_backend,
)


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv(
    "/home/ec2-user/loandocx/.env",
    override=True
)

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError(
        "OPENAI_API_KEY is not loaded from /home/ec2-user/loandocx/.env"
    )

client = OpenAI(api_key=api_key)


# ============================================================
# OPENAI FUNCTION TOOLS
# ============================================================

tools = [

    {
        "type": "function",
        "name": "check_dns",
        "description": (
            "Check whether the LoanDocX hostname resolves correctly "
            "using DNS."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },

    {
        "type": "function",
        "name": "check_https",
        "description": (
            "Check whether the LoanDocX public website is reachable "
            "over HTTPS. Returns the HTTP status and related information."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },

    {
        "type": "function",
        "name": "check_nginx",
        "description": (
            "Check whether Nginx is running. "
            "This checks the Nginx service state only. "
            "It does not restart Nginx."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },

    {
        "type": "function",
        "name": "check_loandocx",
        "description": (
            "Check the systemd state of loandocx.service. "
            "Returns whether the LoanDocX service is RUNNING "
            "or NOT_RUNNING. "
            "This does not test the TCP port or HTTP endpoint."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },

    {
        "type": "function",
        "name": "restart_loandocx",
        "description": (
            "AUTONOMOUS RECOVERY ACTION. "
            "Restart loandocx.service. "
            "Use this only when diagnostic evidence clearly shows "
            "that loandocx.service is NOT_RUNNING and the service "
            "is the likely cause of the website outage. "
            "This action changes the server state."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },

    {
        "type": "function",
        "name": "check_loandocx_port",
        "description": (
            "Check whether TCP port 7860 on 127.0.0.1 is accepting "
            "connections. This checks the application's listening "
            "port only."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },

    {
        "type": "function",
        "name": "check_backend",
        "description": (
            "Make a direct HTTP request to "
            "http://127.0.0.1:7860/ to verify that the LoanDocX "
            "application itself responds, bypassing Nginx."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },

    {
        "type": "function",
        "name": "check_nginx_upstream",
        "description": (
            "Inspect the Nginx configuration and report the "
            "proxy_pass or upstream configuration used to reach "
            "the LoanDocX backend."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },

    {
        "type": "function",
        "name": "check_nginx_error_log",
        "description": (
            "Read recent Nginx error log entries to identify "
            "proxy or upstream errors such as connection refused "
            "or HTTP 502-related failures."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },

    {
        "type": "function",
        "name": "check_loandocx_logs",
        "description": (
            "Read recent systemd journal entries for "
            "loandocx.service to identify application startup "
            "or runtime errors."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },
]


# ============================================================
# TOOL REGISTRIES
# ============================================================

diagnostic_tools = {
    "check_dns",
    "check_https",
    "check_nginx",
    "check_loandocx",
    "check_loandocx_port",
    "check_backend",
    "check_nginx_upstream",
    "check_nginx_error_log",
    "check_loandocx_logs",
}

recovery_tools = {
    "restart_loandocx",
}


TOOL_FUNCTIONS = {
    "check_dns": check_dns,
    "check_https": check_https,
    "check_nginx": check_nginx,
    "check_loandocx": check_loandocx,
    "check_loandocx_port": check_loandocx_port,
    "check_backend": check_backend,
    "check_nginx_upstream": check_nginx_upstream,
    "check_nginx_error_log": check_nginx_error_log,
    "check_loandocx_logs": check_loandocx_logs,
    "restart_loandocx": restart_loandocx,
}


# ============================================================
# AGENT PROMPT
# ============================================================

SYSTEM_PROMPT = """

You are an autonomous server monitoring and incident-recovery AI
agent responsible for diagnosing and recovering the LoanDocX website.

You have access only to the tools provided to you.

============================================================
CORE RULES
============================================================

1. TOOL EXECUTION TRUTH

You may only claim that a check was performed if the controller
actually executed the corresponding tool.

Never invent tool results.

Never simulate tool execution.

Never assume that a tool was executed.

Never fabricate a Linux command result.

------------------------------------------------------------

2. TOOL RESULT IDENTITY

Every tool result belongs only to the tool that produced it.

For example:

check_loandocx

may report:

{
    "status": "NOT_RUNNING",
    "service": "loandocx.service"
}

That result must NEVER be reported as the result of:

check_loandocx_port
check_backend
check_nginx_upstream
check_nginx_error_log

Each tool has an independent meaning.

------------------------------------------------------------

3. LINUX COMMANDS

Do not claim to have executed:

curl
dig
nslookup
systemctl
journalctl
openssl
ss
grep
tail
traceroute
nmap

unless one of the available tools actually executes them.

If useful commands need to be suggested to the administrator,
put them only under:

OPTIONAL HUMAN COMMANDS

and explicitly say:

"Not executed by the agent."

------------------------------------------------------------

4. DUPLICATE CHECKS

Do not repeatedly call a diagnostic tool when its result is
already known and the relevant system state has not changed.

After a restart, checks related to the changed application state
must be performed again.

============================================================
NORMAL INITIAL DIAGNOSTICS
============================================================

Normally establish:

1. check_dns
2. check_https
3. check_nginx
4. check_loandocx

These are the primary outage checks.

============================================================
SAFE RECOVERY
============================================================

If the following evidence is established:

DNS = OK

AND

HTTPS indicates HTTP 502 or another backend/proxy outage

AND

Nginx = RUNNING

AND

loandocx.service = NOT_RUNNING

then restart_loandocx is justified.

Execute the recovery action.

Do not merely recommend it.

Do not ask the user for confirmation.

============================================================
RECOVERY VERIFICATION
============================================================

After restart_loandocx is executed, verify the changed state.

Call:

1. check_loandocx
2. check_loandocx_port
3. check_backend
4. check_https

Recovery is successful only when:

check_loandocx = RUNNING

AND

check_loandocx_port = OPEN

AND

check_backend indicates HTTP 200

AND

check_https indicates HTTP 200

When all four conditions are satisfied:

STOP INVESTIGATION.

Do not start another diagnostic cycle.

============================================================
POST-RECOVERY FAILURE
============================================================

If recovery was attempted but the website remains unhealthy,
investigate the remaining problem.

For example:

LoanDocX service = RUNNING
port = OPEN
backend = HTTP 200
HTTPS = HTTP 502

This indicates that the application is healthy locally but
the public Nginx path is still failing.

Then investigate:

1. check_nginx_upstream
2. check_nginx_error_log

If application logs are relevant, also use:

3. check_loandocx_logs

Do not repeatedly restart LoanDocX merely because HTTPS remains
unhealthy.

============================================================
FINAL BEHAVIOR
============================================================

Use actual tool results to make decisions.

Execute safe recovery when justified.

Verify recovery.

Do not repeat completed checks unnecessarily.

Do not confuse one tool's result with another tool.

When sufficient evidence has been collected, stop.
"""


# ============================================================
# CONTROLLER STATE
# ============================================================

executed_diagnostics = {}

executed_tool_history = []

recovery_executed = False

MAX_CONTROLLER_CYCLES = 6

controller_cycle = 0

investigation_finished = False

# ============================================================
# INCIDENT HISTORY
# ============================================================

INCIDENT_HISTORY_FILE = "/home/ec2-user/recovery-agent/incidents.json"


def save_incident(
    status,
    diagnosis="",
    recovery_action=None,
    verification=None,
):
    """
    Save the current investigation as a persistent incident record.

    status:
        HEALTHY
        RECOVERED
        FAILED
    """

    incident = {
        "incident_id": datetime.now().strftime(
            "INC-%Y%m%d-%H%M%S"
        ),
        "timestamp": datetime.now().isoformat(),
        "status": status,
        "recovery_action": recovery_action,
        "diagnosis": diagnosis,
        "verification": verification or {},
        "tool_history": executed_tool_history.copy(),
    }

    try:

        # -----------------------------------------------
        # Read existing history
        # -----------------------------------------------

        if os.path.exists(INCIDENT_HISTORY_FILE):

           try:

             with open(
                  INCIDENT_HISTORY_FILE,
                  "r",
                  encoding="utf-8",
                ) as f:

                content = f.read().strip()

             if not content:
               incidents = []

             else:
               incidents = json.loads(content)

               if not isinstance(incidents, list):
                  incidents = []

           except (json.JSONDecodeError, OSError):

                  incidents = []

        else:

           incidents = []

        # -----------------------------------------------
        # Add current incident
        # -----------------------------------------------

        incidents.append(incident)

        # -----------------------------------------------
        # Save history
        # -----------------------------------------------

        with open(
            INCIDENT_HISTORY_FILE,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                incidents,
                f,
                indent=2,
                default=str,
            )

        print("\n")
        print("=" * 60)
        print("INCIDENT HISTORY SAVED")
        print("=" * 60)

        print(
            "Incident ID:",
            incident["incident_id"],
        )

        print(
            "Status:",
            status,
        )

        print(
            "History file:",
            INCIDENT_HISTORY_FILE,
        )

        return incident

    except Exception as exc:

        print("\n")
        print("=" * 60)
        print("INCIDENT HISTORY SAVE FAILED")
        print("=" * 60)

        print(
            type(exc).__name__,
            str(exc),
        )

        return None

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def record_tool_result(tool_name, result, purpose=None):
    """
    Record an actual tool execution in the permanent history.
    """

    entry = {
        "tool": tool_name,
        "result": result,
    }

    if purpose:
        entry["purpose"] = purpose

    executed_tool_history.append(entry)


def get_status(result):
    """
    Safely extract a status from a tool result.
    """

    if isinstance(result, dict):
        return result.get("status")

    return None


def get_http_status(result):
    """
    Safely extract an HTTP status from a tool result.

    Different tools may use different keys.
    """

    if not isinstance(result, dict):
        return None

    for key in (
        "http_status",
        "status_code",
        "http_code",
    ):
        value = result.get(key)

        if isinstance(value, int):
            return value

    return None


def https_indicates_backend_failure(result):
    """
    Determine whether HTTPS evidence indicates a backend/proxy
    outage.
    """

    status = get_http_status(result)

    if status == 502:
        return True

    if status in (503, 504):
        return True

    return False


def recovery_is_justified():
    """
    Python safety gate.

    The LLM can request restart_loandocx, but Python independently
    verifies that the known evidence actually justifies the restart.
    """

    dns_result = executed_diagnostics.get("check_dns")
    https_result = executed_diagnostics.get("check_https")
    nginx_result = executed_diagnostics.get("check_nginx")
    loandocx_result = executed_diagnostics.get("check_loandocx")

    if dns_result is None:
        return False

    if https_result is None:
        return False

    if nginx_result is None:
        return False

    if loandocx_result is None:
        return False

    dns_status = get_status(dns_result)
    nginx_status = get_status(nginx_result)
    loandocx_status = get_status(loandocx_result)

    return (
        dns_status == "OK"
        and https_indicates_backend_failure(https_result)
        and nginx_status == "RUNNING"
        and loandocx_status == "NOT_RUNNING"
    )


def execute_tool(tool_name):
    """
    Execute one actual Python tool.
    """

    function = TOOL_FUNCTIONS.get(tool_name)

    if function is None:
        return {
            "status": "ERROR",
            "error": f"Unknown tool: {tool_name}",
        }

    try:
        result = function()

        return result

    except Exception as exc:

        return {
            "status": "ERROR",
            "error": f"{type(exc).__name__}: {str(exc)}",
        }


# ============================================================
# FINAL AI DIAGNOSIS
# ============================================================

def produce_final_diagnosis():

    final_prompt = f"""

You are generating the final diagnosis for an autonomous
LoanDocX server monitoring agent.

Do not call tools.

Use ONLY the actual execution history below.

============================================================
ACTUAL TOOL EXECUTION HISTORY
============================================================

{json.dumps(executed_tool_history, indent=2, default=str)}

============================================================

Return exactly these sections:

CHECKS ACTUALLY EXECUTED

List every tool that was actually executed and its actual result.

Do not list tools merely requested by the LLM if the controller
did not execute them.

Do not invent results.

DIAGNOSIS

Explain what the evidence means.

If recovery was performed, explain:

1. Why recovery was triggered.
2. What recovery action was executed.
3. What verification showed.
4. Whether recovery was successful.

Do not claim recovery succeeded unless the verification evidence
supports it.

OPTIONAL HUMAN COMMANDS

Only include this section if additional investigation is required.

Any command listed here must explicitly say:

"Not executed by the agent."

"""

    try:

        final_response = client.responses.create(
            model="gpt-5-mini",
            input=[
                {
                    "role": "user",
                    "content": final_prompt,
                }
            ],
            tools=[],
        )

        return final_response.output_text

    except Exception as exc:

        return (
            "CHECKS ACTUALLY EXECUTED\n\n"
            f"{json.dumps(executed_tool_history, indent=2, default=str)}\n\n"
            "DIAGNOSIS\n\n"
            "Final AI diagnosis generation failed.\n"
            f"Error: {type(exc).__name__}: {str(exc)}\n\n"
            "OPTIONAL HUMAN COMMANDS\n\n"
            "No commands were executed by the agent."
        )


# ============================================================
# INITIAL CONTROLLER INPUT
# ============================================================

conversation = [

    {
        "role": "system",
        "content": SYSTEM_PROMPT,
    },

    {
        "role": "user",
        "content": (
            "Diagnose the current LoanDocX website and recover it "
            "automatically if a safe recovery action is clearly "
            "justified."
        ),
    },
]
# ============================================================
# RECOVERY READINESS VERIFICATION
# ============================================================

def verify_recovery_with_retry(
    max_wait_seconds=30,
    retry_interval=3,
):
    """
    Wait for LoanDocX to become fully ready after restart.

    The systemd service may become RUNNING before the
    Gradio application has finished binding to port 7860.
    Therefore, verification is retried for a short period.
    """

    start_time = time.time()

    latest_results = {}

    while True:

        elapsed = int(time.time() - start_time)

        print("\n")
        print("-" * 60)
        print(
            f"RECOVERY READINESS CHECK "
            f"({elapsed}/{max_wait_seconds} seconds)"
        )
        print("-" * 60)

        # ----------------------------------------------------
        # SERVICE
        # ----------------------------------------------------

        loandocx_result = execute_tool(
            "check_loandocx"
        )

        print("\nLoanDocX service:")
        print(
            json.dumps(
                loandocx_result,
                indent=2,
                default=str,
            )
        )

        # ----------------------------------------------------
        # PORT
        # ----------------------------------------------------

        port_result = execute_tool(
            "check_loandocx_port"
        )

        print("\nPort 7860:")
        print(
            json.dumps(
                port_result,
                indent=2,
                default=str,
            )
        )

        # ----------------------------------------------------
        # BACKEND
        # ----------------------------------------------------

        backend_result = execute_tool(
            "check_backend"
        )

        print("\nBackend:")
        print(
            json.dumps(
                backend_result,
                indent=2,
                default=str,
            )
        )

        # ----------------------------------------------------
        # HTTPS
        # ----------------------------------------------------

        https_result = execute_tool(
            "check_https"
        )

        print("\nPublic HTTPS:")
        print(
            json.dumps(
                https_result,
                indent=2,
                default=str,
            )
        )

        latest_results = {
            "check_loandocx": loandocx_result,
            "check_loandocx_port": port_result,
            "check_backend": backend_result,
            "check_https": https_result,
        }

        # ----------------------------------------------------
        # DETERMINE HEALTH
        # ----------------------------------------------------

        service_ok = (
            isinstance(loandocx_result, dict)
            and loandocx_result.get("status") == "RUNNING"
        )

        port_ok = (
            isinstance(port_result, dict)
            and port_result.get("status") == "OPEN"
        )

        backend_ok = (
            isinstance(backend_result, dict)
            and backend_result.get("status") == "RESPONDING"
            and get_http_status(backend_result) == 200
        )

        https_ok = (
            isinstance(https_result, dict)
            and get_http_status(https_result) == 200
        )

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        if (
            service_ok
            and port_ok
            and backend_ok
            and https_ok
        ):

            print("\n")
            print("=" * 60)
            print("RECOVERY READINESS ACHIEVED")
            print("=" * 60)

            return True, latest_results

        # ----------------------------------------------------
        # TIMEOUT
        # ----------------------------------------------------

        if elapsed >= max_wait_seconds:

            print("\n")
            print("=" * 60)
            print("RECOVERY READINESS TIMEOUT")
            print("=" * 60)

            return False, latest_results

        # ----------------------------------------------------
        # WAIT
        # ----------------------------------------------------

        print(
            f"\nApplication still starting. "
            f"Waiting {retry_interval} seconds..."
        )

        time.sleep(retry_interval)

# ============================================================
# MAIN CONTROLLER
# ============================================================

while (
    controller_cycle < MAX_CONTROLLER_CYCLES
    and not investigation_finished
):

    controller_cycle += 1

    print("\n")
    print("=" * 60)
    print(
        f"CONTROLLER CYCLE "
        f"{controller_cycle}/{MAX_CONTROLLER_CYCLES}"
    )
    print("=" * 60)

    # --------------------------------------------------------
    # ASK LLM
    # --------------------------------------------------------

    print("\nSENDING REQUEST TO LLM...")

    try:

        response = client.responses.create(
            model="gpt-5-mini",
            input=conversation,
            tools=tools,
        )

    except Exception as exc:

        print("\nLLM ERROR:")
        print(type(exc).__name__, str(exc))

        break

    # --------------------------------------------------------
    # PRESERVE THE MODEL RESPONSE
    #
    # This is critical.
    #
    # The previous version did not send the response output
    # back into the next Responses API call.
    # --------------------------------------------------------

    conversation.extend(response.output)

    # --------------------------------------------------------
    # FIND FUNCTION CALLS
    # --------------------------------------------------------

    tool_calls = [
        item
        for item in response.output
        if getattr(item, "type", None) == "function_call"
    ]

    # --------------------------------------------------------
    # NO TOOL CALL
    # --------------------------------------------------------

    if not tool_calls:

        print("\n")
        print("=" * 60)
        print("FINAL AI DIAGNOSIS")
        print("=" * 60)
    
        print(response.output_text)
    
        # --------------------------------------------------------
        # Determine whether this was a healthy investigation.
        # --------------------------------------------------------
    
        if not recovery_executed:
    
            save_incident(
                status="HEALTHY",
                diagnosis=response.output_text,
                recovery_action=None,
                verification={
                    "website": "HEALTHY",
                    "recovery_required": False,
                },
            )
    
        investigation_finished = True
    
        break
    # --------------------------------------------------------
    # EXECUTE REQUESTED TOOLS
    # --------------------------------------------------------

    tool_outputs = []

    for item in tool_calls:

        tool_name = item.name

        print("\n")
        print("-" * 60)
        print("OUTPUT TYPE: function_call")
        print("LLM REQUESTED TOOL:", tool_name)
        print("-" * 60)

        # ====================================================
        # UNKNOWN TOOL
        # ====================================================

        if (
            tool_name not in diagnostic_tools
            and tool_name not in recovery_tools
        ):

            result = {
                "status": "ERROR",
                "error": f"Unknown tool: {tool_name}",
            }

            print("TOOL RESULT:")
            print(json.dumps(result, indent=2, default=str))

            tool_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps(result),
                }
            )

            continue

        # ====================================================
        # PREVENT DUPLICATE DIAGNOSTIC EXECUTION
        # ====================================================

        if (
            tool_name in diagnostic_tools
            and tool_name in executed_diagnostics
        ):

            print(
                f"CONTROLLER: {tool_name} already has an "
                f"established result."
            )

            result = executed_diagnostics[tool_name]

            print("CONTROLLER: Diagnostic NOT executed again.")
            print("USING ESTABLISHED RESULT:")
            print(json.dumps(result, indent=2, default=str))

            tool_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps(result),
                }
            )

            continue

        # ====================================================
        # RECOVERY SAFETY GATE
        # ====================================================

        if tool_name == "restart_loandocx":

            # -----------------------------------------------
            # Do not allow multiple restarts in one incident.
            # -----------------------------------------------

            if recovery_executed:

                result = {
                    "status": "BLOCKED",
                    "reason": (
                        "restart_loandocx was already executed "
                        "during this investigation."
                    ),
                }

                print("RECOVERY BLOCKED:")
                print(json.dumps(result, indent=2))

                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps(result),
                    }
                )

                continue

            # -----------------------------------------------
            # Independent Python safety check.
            # -----------------------------------------------

            if not recovery_is_justified():

                result = {
                    "status": "BLOCKED",
                    "reason": (
                        "Recovery was requested, but the Python "
                        "controller does not have sufficient "
                        "evidence to safely restart loandocx.service."
                    ),
                }

                print("RECOVERY BLOCKED:")
                print(json.dumps(result, indent=2))

                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps(result),
                    }
                )

                continue

            # -----------------------------------------------
            # Execute actual restart.
            # -----------------------------------------------

            print("\n")
            print("=" * 60)
            print("AUTONOMOUS RECOVERY")
            print("=" * 60)

            print(
                "Reason: DNS is healthy, HTTPS indicates backend "
                "failure, Nginx is running, and LoanDocX service "
                "is NOT_RUNNING."
            )

            print("Executing restart_loandocx...")

            result = execute_tool(tool_name)

            recovery_executed = True

            record_tool_result(
                tool_name,
                result,
                purpose="autonomous recovery",
            )

            print("RECOVERY TOOL RESULT:")
            print(json.dumps(result, indent=2, default=str))

            # ------------------------------------------------
            # Important:
            #
            # After restart, old application state is stale.
            # Remove those cached results.
            # ------------------------------------------------

            executed_diagnostics.pop(
                "check_loandocx",
                None,
            )

            executed_diagnostics.pop(
                "check_loandocx_port",
                None,
            )

            executed_diagnostics.pop(
                "check_backend",
                None,
            )

            executed_diagnostics.pop(
                "check_https",
                None,
            )

            tool_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps(result),
                }
            )

            continue

        # ====================================================
        # DIAGNOSTIC TOOL EXECUTION
        # ====================================================

        result = execute_tool(tool_name)

        executed_diagnostics[tool_name] = result

        record_tool_result(
            tool_name,
            result,
            purpose="diagnostic",
        )

        print("TOOL RESULT:")
        print(json.dumps(result, indent=2, default=str))

        tool_outputs.append(
            {
                "type": "function_call_output",
                "call_id": item.call_id,
                "output": json.dumps(result),
            }
        )

    # ========================================================
    # SEND ACTUAL TOOL RESULTS BACK TO THE LLM
    # ========================================================

    conversation.extend(tool_outputs)

    print("\n")
    print("=" * 60)
    print("TOOL RESULTS RETURNED TO LLM")
    print("=" * 60)

    for output in tool_outputs:

        print(
            "call_id:",
            output["call_id"],
        )

        print(
            "output:",
            output["output"],
        )

    # ========================================================
    # CHECK WHETHER RECOVERY WAS EXECUTED
    # ========================================================

    # ========================================================
    # RECOVERY READINESS VERIFICATION
    # ========================================================

    if recovery_executed:

        print("\n")
        print("=" * 60)
        print("RECOVERY VERIFICATION")
        print("=" * 60)

        print(
            "\nWaiting for LoanDocX application "
            "to become fully ready..."
        )

        recovery_success, verification_results = (
            verify_recovery_with_retry(
                max_wait_seconds=30,
                retry_interval=3,
            )
        )

        # ----------------------------------------------------
        # RECORD VERIFICATION RESULTS
        # ----------------------------------------------------

        for tool_name, result in verification_results.items():

            record_tool_result(
                tool_name,
                result,
                purpose="recovery verification",
            )

        # ----------------------------------------------------
        # DISPLAY FINAL VERIFICATION
        # ----------------------------------------------------

        loandocx_result = verification_results[
            "check_loandocx"
        ]

        port_result = verification_results[
            "check_loandocx_port"
        ]

        backend_result = verification_results[
            "check_backend"
        ]

        https_result = verification_results[
            "check_https"
        ]

        service_ok = (
            isinstance(loandocx_result, dict)
            and loandocx_result.get("status") == "RUNNING"
        )

        port_ok = (
            isinstance(port_result, dict)
            and port_result.get("status") == "OPEN"
        )

        backend_ok = (
            isinstance(backend_result, dict)
            and backend_result.get("status") == "RESPONDING"
            and get_http_status(backend_result) == 200
        )

        https_ok = (
            isinstance(https_result, dict)
            and get_http_status(https_result) == 200
        )

        print("\n")
        print("=" * 60)
        print("RECOVERY VERIFICATION RESULT")
        print("=" * 60)

        print(
            "Service RUNNING:",
            service_ok,
        )

        print(
            "Port OPEN:",
            port_ok,
        )

        print(
            "Backend HTTP 200:",
            backend_ok,
        )

        print(
            "HTTPS HTTP 200:",
            https_ok,
        )

        # ====================================================
        # RECOVERY SUCCESS
        # ====================================================

        if recovery_success:

            print("\nRECOVERY SUCCESSFUL")

            final_text = produce_final_diagnosis()

             # --------------------------------------------------------
             # Save successful recovery incident
             # --------------------------------------------------------

            save_incident( 
                  status="RECOVERED",
                  diagnosis=final_text,
                  recovery_action="restart_loandocx",
                  verification={
                 "service": loandocx_result,
                 "port": port_result,
                 "backend": backend_result,
                 "https": https_result,
                 },
            )  
            
            print("\n")
            print("=" * 60)
            print("FINAL AI DIAGNOSIS")
            print("=" * 60)

            print(final_text)

            investigation_finished = True

            break

        # ====================================================
        # RECOVERY NOT SUCCESSFUL
        # ====================================================

        print("\nRECOVERY NOT FULLY SUCCESSFUL")
                # ----------------------------------------------------
        # Save failed recovery incident
        # ----------------------------------------------------

        failure_diagnosis = (
            "Automatic recovery was attempted but "
            "the application did not become fully healthy "
            "within the recovery readiness window."
        )

        save_incident(
            status="FAILED",
            diagnosis=failure_diagnosis,
            recovery_action="restart_loandocx",
            verification={
                "service": loandocx_result,
                "port": port_result,
                "backend": backend_result,
                "https": https_result,
            },
        )

        conversation.append(
            {
                "role": "user",
                "content": (
                    "Recovery verification completed after "
                    "waiting for application readiness. "
                    "Do not restart loandocx.service again. "
                    "Investigate the remaining problem using "
                    "appropriate diagnostic tools.\n\n"
                    + json.dumps(
                        verification_results,
                        indent=2,
                        default=str,
                    )
                ),
            }
        )

        continue

# ============================================================
# MAX CYCLE HANDLING
# ============================================================

if (
    controller_cycle >= MAX_CONTROLLER_CYCLES
    and not investigation_finished
):

    print("\n")
    print("=" * 60)
    print("MAXIMUM CONTROLLER CYCLES REACHED")
    print("=" * 60)

    print(
        "The agent stopped to prevent an unexpected tool loop."
    )

    final_text = produce_final_diagnosis()

    print("\n")
    print("=" * 60)
    print("FINAL AI DIAGNOSIS")
    print("=" * 60)

    print(final_text)
