import socket
import subprocess
import requests
import json

WEBSITE_HOST = "loandocx-agentai-demo.duckdns.org"
WEBSITE_URL = f"https://{WEBSITE_HOST}"

# LoanDocX is currently expected to run on Gradio port 7860.
LOANDOCX_HOST = "127.0.0.1"
LOANDOCX_PORT = 7860


# ============================================================
# DNS
# ============================================================

def check_dns():
    try:
        ip_address = socket.gethostbyname(WEBSITE_HOST)

        return {
            "status": "OK",
            "hostname": WEBSITE_HOST,
            "resolved_ip": ip_address
        }

    except socket.gaierror as e:
        return {
            "status": "DNS_ERROR",
            "hostname": WEBSITE_HOST,
            "error": str(e)
        }


# ============================================================
# HTTPS
# ============================================================

def check_https():
    try:
        response = requests.get(
            WEBSITE_URL,
            timeout=10,
            verify=False
        )

        return {
            "status": "OK",
            "http_status": response.status_code,
            "url": WEBSITE_URL
        }

    except requests.exceptions.SSLError as e:

        return {
            "status": "CERTIFICATE_ERROR",
            "error": str(e),
            "url": WEBSITE_URL
        }

    except requests.exceptions.ConnectionError as e:

        return {
            "status": "CONNECTION_ERROR",
            "error": str(e),
            "url": WEBSITE_URL
        }

    except requests.exceptions.Timeout as e:

        return {
            "status": "TIMEOUT",
            "error": str(e),
            "url": WEBSITE_URL
        }

    except Exception as e:

        return {
            "status": "ERROR",
            "error": str(e),
            "url": WEBSITE_URL
        }


# ============================================================
# PORT CHECK
# ============================================================

def check_port(host, port, timeout=5):
    try:

        with socket.create_connection(
            (host, port),
            timeout=timeout
        ):

            return {
                "status": "OPEN",
                "host": host,
                "port": port
            }

    except socket.timeout:

        return {
            "status": "TIMEOUT",
            "host": host,
            "port": port
        }

    except ConnectionRefusedError:

        return {
            "status": "CLOSED",
            "host": host,
            "port": port
        }

    except OSError as e:

        return {
            "status": "ERROR",
            "host": host,
            "port": port,
            "error": str(e)
        }


# ============================================================
# NGINX STATUS
# ============================================================

def check_nginx():

    try:

        result = subprocess.run(
            ["systemctl", "is-active", "nginx"],
            capture_output=True,
            text=True,
            timeout=5
        )

        status = result.stdout.strip()

        if status == "active":

            return {
                "status": "RUNNING",
                "service": "nginx"
            }

        return {
            "status": "NOT_RUNNING",
            "service": "nginx",
            "systemctl_status": status,
            "error": result.stderr.strip()
        }

    except subprocess.TimeoutExpired:

        return {
            "status": "TIMEOUT",
            "service": "nginx"
        }

    except Exception as e:

        return {
            "status": "ERROR",
            "service": "nginx",
            "error": str(e)
        }


# ============================================================
# LOANDOCX SERVICE STATUS
# ============================================================

def check_loandocx():

    try:

        result = subprocess.run(
            ["systemctl", "is-active", "loandocx.service"],
            capture_output=True,
            text=True,
            timeout=5
        )

        status = result.stdout.strip()

        if status == "active":

            return {
                "status": "RUNNING",
                "service": "loandocx.service"
            }

        return {
            "status": "NOT_RUNNING",
            "service": "loandocx.service",
            "systemctl_status": status,
            "error": result.stderr.strip()
        }

    except subprocess.TimeoutExpired:

        return {
            "status": "TIMEOUT",
            "service": "loandocx.service"
        }

    except Exception as e:

        return {
            "status": "ERROR",
            "service": "loandocx.service",
            "error": str(e)
        }


# ============================================================
# RECOVERY
# ============================================================

def restart_loandocx():

    try:

        result = subprocess.run(
            [
                "sudo",
                "systemctl",
                "restart",
                "loandocx.service"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:

            return {
                "status": "RESTART_COMMAND_SUCCESS",
                "service": "loandocx.service"
            }

        return {
            "status": "RESTART_FAILED",
            "service": "loandocx.service",
            "error": result.stderr.strip()
        }

    except Exception as e:

        return {
            "status": "ERROR",
            "service": "loandocx.service",
            "error": str(e)
        }


# ============================================================
# STAGE 2
# NGINX ERROR LOG
# ============================================================

def check_nginx_error_log():

    try:

        result = subprocess.run(
            [
                "sudo",
                "tail",
                "-n",
                "100",
                "/var/log/nginx/error.log"
            ],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:

            return {
                "status": "ERROR",
                "source": "/var/log/nginx/error.log",
                "error": result.stderr.strip()
            }

        log = result.stdout.strip()

        if not log:

            return {
                "status": "EMPTY",
                "source": "/var/log/nginx/error.log"
            }

        return {
            "status": "OK",
            "source": "/var/log/nginx/error.log",
            "lines": log
        }

    except subprocess.TimeoutExpired:

        return {
            "status": "TIMEOUT",
            "source": "/var/log/nginx/error.log"
        }

    except Exception as e:

        return {
            "status": "ERROR",
            "source": "/var/log/nginx/error.log",
            "error": str(e)
        }


# ============================================================
# LOANDOCX APPLICATION LOG
# ============================================================

def check_loandocx_logs():

    try:

        result = subprocess.run(
            [
                "sudo",
                "journalctl",
                "-u",
                "loandocx.service",
                "-n",
                "100",
                "--no-pager"
            ],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:

            return {
                "status": "ERROR",
                "service": "loandocx.service",
                "error": result.stderr.strip()
            }

        log = result.stdout.strip()

        if not log:

            return {
                "status": "EMPTY",
                "service": "loandocx.service"
            }

        return {
            "status": "OK",
            "service": "loandocx.service",
            "lines": log
        }

    except subprocess.TimeoutExpired:

        return {
            "status": "TIMEOUT",
            "service": "loandocx.service"
        }

    except Exception as e:

        return {
            "status": "ERROR",
            "service": "loandocx.service",
            "error": str(e)
        }


# ============================================================
# LOANDOCX LISTENING PORT
# ============================================================

def check_loandocx_port():

    result = check_port(
        LOANDOCX_HOST,
        LOANDOCX_PORT
    )

    result["service"] = "loandocx.service"
    result["expected_port"] = LOANDOCX_PORT

    return result


# ============================================================
# NGINX UPSTREAM CONFIGURATION
# ============================================================

def check_nginx_upstream():

    try:

        result = subprocess.run(
            [
                "sudo",
                "nginx",
                "-T"
            ],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:

            return {
                "status": "ERROR",
                "error": result.stderr.strip()
            }

        config = result.stdout

        proxy_lines = []

        upstream_lines = []

        for line in config.splitlines():

            stripped = line.strip()

            if "proxy_pass" in stripped:
                proxy_lines.append(stripped)

            if stripped.startswith("upstream "):
                upstream_lines.append(stripped)

        return {
            "status": "OK",
            "proxy_pass": proxy_lines,
            "upstream_blocks": upstream_lines
        }

    except subprocess.TimeoutExpired:

        return {
            "status": "TIMEOUT"
        }

    except Exception as e:

        return {
            "status": "ERROR",
            "error": str(e)
        }


# ============================================================
# DIRECT BACKEND TEST
# ============================================================

def check_backend():
    url = "http://127.0.0.1:7860/"

    try:
        response = requests.get(
            url,
            timeout=10
        )

        return {
            "status": "RESPONDING",
            "http_status": response.status_code,
            "url": url
        }

    except requests.exceptions.ConnectionError as e:
        return {
            "status": "CONNECTION_ERROR",
            "url": url,
            "error": str(e)
        }

    except requests.exceptions.Timeout as e:
        return {
            "status": "TIMEOUT",
            "url": url,
            "error": str(e)
        }

    except Exception as e:
        return {
            "status": "ERROR",
            "url": url,
            "error": str(e)
        }
def check_nginx_local_proxy():
    import requests

    try:
        response = requests.get(
            "http://127.0.0.1:7860/",
            timeout=10
        )

        return {
            "status": "OK",
            "http_status": response.status_code,
            "url": "http://127.0.0.1:7860/"
        }

    except Exception as e:
        return {
            "status": "ERROR",
            "error": str(e)
        }


def check_nginx_config():
    import subprocess

    try:
        result = subprocess.run(
            ["sudo", "nginx", "-T"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return {
                "status": "OK",
                "config": result.stdout
            }

        return {
            "status": "ERROR",
            "error": result.stderr
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "TIMEOUT"
        }

    except Exception as e:
        return {
            "status": "ERROR",
            "error": str(e)
        }        
# ============================================================
# BASIC DIAGNOSTIC REPORT
# ============================================================

def diagnose():

    return {
        "dns": check_dns(),
        "https": check_https(),
        "nginx": check_nginx(),
        "loandocx": check_loandocx(),
        "loandocx_port": check_loandocx_port()
    }


# ============================================================
# MANUAL TEST
# ============================================================

if __name__ == "__main__":

    print("DIAGNOSTIC REPORT")
    print("=================")

    result = diagnose()

    print(json.dumps(result, indent=2))
