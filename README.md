# Loandocx_recovery_agent
he LoanDocX AI Recovery Agent watches the public LoanDocX site and fixes one common outage on its own.  The site is a Gradio app (loandocx.service on port 7860) behind Nginx. When the page is down, agent.py asks a model which checks to run: DNS, public HTTPS, Nginx, the app service, the local port, and the app itself.
