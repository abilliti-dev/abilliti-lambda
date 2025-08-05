# Abilliti Lambda Functions

This repository contains the Python Lambda functions used by the [Abilliti](https://abilliti.com) backend infrastructure. It is consumed as a **Git submodule** by the CDK infrastructure repo (`abilliti-backend-cdk`) and is automatically deployed when changes are pushed to `main`.

---

## 📁 Project Structure

\`\`\`
lambdas/
├── handlers/
│   ├── __init__.py
│   └── ...             # Additional modular handler logic
├── lambda_function.py  # Lambda entrypoint
├── router.py           # Event routing logic
├── requirements.txt    # Dependencies
\`\`\`

- **\`lambda_function.py\`**: Lambda entrypoint exposing \`lambda_handler\`
- **\`router.py\`**: Routes events to appropriate functions in \`handlers/\`
- **\`handlers/\`**: Modular logic broken out by function or route
- **\`requirements.txt\`**: Optional Python dependencies

---

## 🚀 Deployment Process

This repo is included as a submodule in [\`abilliti-backend-cdk\`](https://github.com/abilliti-dev/abilliti-backend-cdk), and is deployed via GitHub Actions.

### ⚙️ Flow:

1. Code is pushed to \`main\` in this repo.
2. A GitHub Actions workflow sends a \`repository_dispatch\` to the CDK repo.
3. The CDK repo:
   - Pulls the latest commit from this submodule.
   - Repackages the Lambda code.
   - Deploys the updated Lambda using \`cdk deploy\`.

### CDK Lambda config:
\`\`\`ts
handler: \"lambda_function.lambda_handler\",
code: Code.fromAsset(path.join(process.cwd(), \"lambdas\")),
runtime: Runtime.PYTHON_3_12,
\`\`\`

---

## 🧪 Local Testing
**NOTE:** This is AI-generated and has not been confirmed to work.

To test the Lambda entrypoint manually:

\`\`\`bash
PYTHONPATH=lambdas python3 -c \"from lambda_function import lambda_handler; print(lambda_handler)\"
\`\`\`

To simulate an event, create a test script like:

\`\`\`python
# test_event.py
from lambda_function import lambda_handler

if __name__ == \"__main__\":
    event = {
        \"httpMethod\": \"GET\",
        \"path\": \"/test\"
    }
    response = lambda_handler(event, None)
    print(response)
\`\`\`

Then run:

\`\`\`bash
PYTHONPATH=lambdas python3 test_event.py
\`\`\`

---

## ➕ Adding New Handlers

To add a new feature or route:

1. Create a new file in \`handlers/\`, e.g. \`invoice.py\`
2. Add your function(s)
3. Update \`router.py\` to include logic for calling the new handler
4. Push changes to \`main\`
5. GitHub Actions will automatically trigger a CDK deployment

