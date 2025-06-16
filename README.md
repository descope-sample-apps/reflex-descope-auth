![Reflex Descope Auth Banner](./reflex_descope_banner.png)

A lightweight plugin that integrates [Descope](https://www.descope.com/) authentication into [Reflex](https://reflex.dev/) apps using the OpenID Connect (OIDC) Authorization Code flow with PKCE.

---

## 📚 Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Setup](#setup)
- [Usage](#usage)
- [Tips & Best Practices](#tips--best-practices)
- [Environment Variables](#environment-variables)
- [Error Handling](#error-handling)
- [Sample App](#sample-app)
- [Contributing](#contributing)
- [License](#license)

---

## ✨ Features

- 🔐 Seamless login via Descope (OIDC + PKCE)
- 🍪 Secure session cookies with local token signing
- 👤 Easy access to user profile info via ID token
- 🔒 JWT-based session verification
- 🚪 Simple logout flow
- 🧩 Extendable base class for custom logic

---

## 📦 Installation

```bash
pip install reflex-descope-auth
```

---

## ⚙️ Setup

### 1. Create a Descope Project

- Go to the [Descope Console](https://app.descope.com/)
- Create a project and a flow (e.g. `sign-up-or-in`)
- Navigate to **Federated Apps**
- Add a **Generic OIDC Application**
- Select the app to see your **Flow Hosting URL** and **Descope OIDC endpoints**

### 2. Add Environment Variables

Create a `.env` file and copy from [`.env.example`](./reflex_descope_demo/.env.example) or export variables directly:

```bash
DESCOPE_PROJECT_ID=<your-descope-project-id>
DESCOPE_REDIRECT_URI=http://localhost:3000/callback
DESCOPE_FLOW_ID=sign-up-or-in
DESCOPE_LOGOUT_REDIRECT_URI=http://localhost:3000
SESSION_SECRET=<secure-random-secret>
```

> You may override the default Descope endpoints with custom domains using additional environment variables (see below).

---

## 🚀 Usage

### Define App State

```python
import reflex as rx
from reflex_descope_auth import DescopeAuthState

class State(DescopeAuthState):
    @rx.event
    async def auth_redirect(self):
        yield DescopeAuthState.finalize_auth()
        yield rx.redirect("/")
```

### Define Pages

```python
@rx.page(route="/callback", on_load=State.auth_redirect)
def callback():
    return rx.center("Logging in...")

@rx.page()
def index():
    return rx.cond(
        State.logged_in,
        rx.text(f"Welcome, {State.userinfo['name']}!"),
        rx.button("Login", on_click=DescopeAuthState.start_login)
    )
```

---

## 💡 Tips & Best Practices

- `start_login()` and `finalize_auth()` handle the entire OIDC flow
- Use `logged_in` and `userinfo` to gate access and display data
- Session tokens are locally signed and verified with `SESSION_SECRET`
- Cookies persist sessions across browser refreshes

> 🔐 Never commit or expose secrets like `SESSION_SECRET` to version control.

---

## 🔧 Environment Variables

| Name                        | Description                                                             |
|----------------------------|-------------------------------------------------------------------------|
| `DESCOPE_PROJECT_ID`       | Your Descope project/client ID (required)                               |
| `DESCOPE_REDIRECT_URI`     | URI Descope redirects to after login (default: `http://localhost:3000/callback`)             |
| `DESCOPE_FLOW_ID`          | Descope flow ID (default: `sign-up-or-in`)                              |
| `DESCOPE_LOGOUT_REDIRECT_URI` | URI to redirect after logout (default: `http://localhost:3000`)        |
| `SESSION_SECRET`           | Secret used to sign session tokens locally (default: `default-secret`)                              |
| `DESCOPE_AUTH_URL`         | (Optional) Override Descope auth endpoint                               |
| `DESCOPE_TOKEN_URL`        | (Optional) Override token exchange endpoint                             |
| `DESCOPE_USERINFO_URL`     | (Optional) Override userinfo endpoint                                   |
| `DESCOPE_LOGOUT_URL`       | (Optional) Override logout endpoint                                     |
| `DESCOPE_JWKS_URL`         | (Optional) Override JWKS URL (useful when using a custom Descope domain) |

---

## ❗ Error Handling

If login fails or required parameters are missing:

- `error_message` will be set in the state
- No exceptions are raised — plugin handles failures gracefully
- You can access and display `State.error_message` in your UI

> Extend `DescopeAuthState` to customize error handling as needed.

---

## 🧪 Sample App

Explore the [reflex_descope_demo](./reflex_descope_demo) folder for a complete working example that includes:

- Login and logout buttons
- Redirect and error handling
- Conditional rendering based on login status

---

## 🤝 Contributing

Contributions, issues, and suggestions are welcome!  
Feel free to open an issue or pull request if you'd like to improve the plugin or documentation.

---

## 📄 License

MIT License. See [LICENSE](./LICENSE).
