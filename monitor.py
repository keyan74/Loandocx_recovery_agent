import requests
import urllib3

urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)

WEBSITE_URL = "https://loandocx-agentai-demo.duckdns.org"


def check_website():
    try:
        response = requests.get(
            WEBSITE_URL,
            timeout=10,
            verify=False
        )

        return {
            "reachable": True,
            "status": "UP",
            "http_status": response.status_code,
            "url": WEBSITE_URL
        }

    except requests.exceptions.SSLError as e:
        return {
            "reachable": True,
            "status": "CERTIFICATE_ERROR",
            "error": str(e),
            "url": WEBSITE_URL
        }

    except requests.exceptions.ConnectionError as e:
        return {
            "reachable": False,
            "status": "CONNECTION_ERROR",
            "error": str(e),
            "url": WEBSITE_URL
        }

    except requests.exceptions.Timeout as e:
        return {
            "reachable": False,
            "status": "TIMEOUT",
            "error": str(e),
            "url": WEBSITE_URL
        }

    except requests.RequestException as e:
        return {
            "reachable": False,
            "status": "REQUEST_ERROR",
            "error": str(e),
            "url": WEBSITE_URL
        }


if __name__ == "__main__":
    result = check_website()
    print(result)
