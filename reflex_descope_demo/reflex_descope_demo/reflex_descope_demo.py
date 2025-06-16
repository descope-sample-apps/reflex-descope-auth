import reflex as rx
from dotenv import load_dotenv
load_dotenv()

from reflex_descope_auth import DescopeAuthState

class State(DescopeAuthState):
    error_message: str = ""
    
    @rx.event
    async def auth_redirect(self):
        yield DescopeAuthState.finalize_auth()
        if getattr(self, "error_message", None):
            yield rx.redirect("/callback")
            return
        yield rx.redirect("/") 

def index() -> rx.Component:
    return rx.center(
        rx.cond(
            State.logged_in,
            rx.vstack(
                rx.heading(f'You are logged in, {State.userinfo.get("name", "User")}!'),
                rx.button(
                    "Logout",
                    on_click=DescopeAuthState.logout,
                    color_scheme="red",
                    radius="large",
                    size="4",
                ),
                align="center",
                justify="center",
                spacing="4",
            ),
            rx.center(
                rx.button(
                    "Login with Descope",
                    on_click=DescopeAuthState.start_login,
                    color_scheme="blue",
                    radius="large",
                    size="4",
                ),
            ),
        ),
        height="100vh",
    )
    
@rx.page(route="/callback", on_load=State.auth_redirect)
def callback() -> rx.Component:
    return rx.center(
        rx.cond(
            State.error_message != "",
            rx.vstack(
                rx.heading("Login Failed", color_scheme="red"),
                rx.text(State.error_message),
                rx.button(
                    "Try Again",
                    on_click=DescopeAuthState.start_login,
                    color_scheme="blue",
                    radius="large",
                    size="4",
                ),
                align="center",
                spacing="4",
                height="100vh",
                justify="center",
            ),
            rx.vstack(
                rx.spinner(size="3"),
                rx.heading("Processing login..."),
                align="center",
                spacing="4",
                height="100vh",
                justify="center",
            ),
        ),
    )
    
app = rx.App()
app.add_page(index)

