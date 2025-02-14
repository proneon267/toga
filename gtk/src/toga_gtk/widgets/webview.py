import inspect
import json
import sys
from http.cookiejar import CookieJar

from travertino.size import at_least

from toga.widgets.webview import CookiesResult, JavaScriptResult

from ..libs import GLib, WebKit2
from .base import Widget


def add(a, b):
    return a + b


class WebView(Widget):
    """GTK WebView implementation."""

    def sub(self, a, b):
        return a - b

    def register_handler(self, handler_method):
        print(inspect.ismethod(handler_method))

        # if inspect.isfunction(handler_method):
        handler_signature = inspect.signature(handler_method)
        handler_parameters = handler_signature.parameters
        parameter_names = [
            parameter_name for parameter_name, parameter in handler_parameters.items()
        ]
        print(str(handler_signature) + "\n" + str(handler_parameters))
        self.content_manager.add_script(
            WebKit2.UserScript.new(
                (
                    f"window.python.{handler_method.__name__} = "
                    f"function {handler_method.__name__}"
                    f"({', '.join(parameter_names)})"
                    "{"
                    "\n\tconst message = JSON.stringify({"
                    "request_id: `${generateUUID()}`,"
                    f'method: "{handler_method.__name__}",'
                    f"args: [{', '.join(parameter_names)}]"
                    "})"
                    "\n\twindow.python_handler.postMessage(message)"
                    "\n}"
                ),
                WebKit2.UserContentInjectedFrames.ALL_FRAMES,
                WebKit2.UserScriptInjectionTime.START,
            )
        )

    def create(self):
        if WebKit2 is None:  # pragma: no cover
            raise RuntimeError(
                "Unable to import WebKit2. Ensure that the system package providing "
                "WebKit2 and its GTK bindings have been installed. See "
                "https://toga.readthedocs.io/en/stable/reference/api/widgets/mapview.html#system-requirements "  # noqa: E501
                "for details."
            )

        def on_message_received(webview, js_message):
            print("Message Received from JS")
            reply = "Python Received message from JS"
            # self.interface.evaluate_javascript(
            #     f"window.python._receiveResult({json.dumps(reply)});"
            # )
            print(js_message.get_js_value().is_string())
            message = js_message.get_js_value().to_string()
            parsed = json.loads(message)
            # python_method = getattr(self, parsed.get("method"))
            # python_method_args = parsed.get("args")
            # res = python_method(*python_method_args)

            print(json.dumps(message))
            # print("jkhkhkhkjh")

        self.content_manager = WebKit2.UserContentManager()
        self.content_manager.register_script_message_handler("python_handler")
        self.content_manager.connect(
            "script-message-received::python_handler", on_message_received
        )
        self.content_manager.add_script(
            WebKit2.UserScript.new(
                """
                function generateUUID() {
                    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                        var r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
                        return v.toString(16);
                    });
                }
                window.python_handler = window.webkit.messageHandlers.python_handler
                window.python = {
                    _receiveResult: function(result) {
                        console.log("Result from Python:", result);
                        alert("Result from Python: " + result);
                    }
                };
                """,
                WebKit2.UserContentInjectedFrames.ALL_FRAMES,
                WebKit2.UserScriptInjectionTime.START,
            )
        )
        self.register_handler(self.sub)
        self.native = WebKit2.WebView.new_with_user_content_manager(
            self.content_manager
        )

        settings = self.native.get_settings()
        settings.set_property("enable-developer-extras", True)

        # The default cache model is WEB_BROWSER, which will
        # use the backing cache to minimize hits on the web server.
        # This can result in stale web content being served, even if
        # the source document (and the web server response) changes.
        context = self.native.get_context()
        context.set_cache_model(WebKit2.CacheModel.DOCUMENT_VIEWER)

        self.native.connect("load-changed", self.gtk_on_load_changed)

        self.load_future = None

    def gtk_on_load_changed(self, widget, load_event, *args):
        if load_event == WebKit2.LoadEvent.FINISHED:
            self.interface.on_webview_load()

            if self.load_future:
                self.load_future.set_result(None)
                self.load_future = None

    def get_url(self):
        url = self.native.get_uri()
        return None if url == "about:blank" else url

    def _loaded(self, data):
        # Internal method to fake a load event.
        self.native.emit("load-changed", WebKit2.LoadEvent.FINISHED)
        return False

    def set_url(self, value, future=None):
        if value:
            self.native.load_uri(value)
        else:
            self.native.load_plain_text("")
            # GTK doesn't emit a load-changed signal when plain text is loaded; so we
            # fake it. We can't emit the signal directly because it will be handled
            # immediately. During creation of an empty webview, the URL is set to None,
            # which means an event can be triggered before the widget instance has
            # finished construction. So, we defer the call with a 0 timeout.
            GLib.timeout_add(0, self._loaded, None)

        self.load_future = future

    def get_user_agent(self):
        return self.native.get_settings().props.user_agent

    def set_user_agent(self, value):
        # replace user agent of webview (webview has own one)
        self.native.get_settings().props.user_agent = value

    def set_content(self, root_url, content):
        self.native.load_html(content, root_url)

    def get_cookies(self):
        # Create the result object
        result = CookiesResult()
        result.set_result(CookieJar())

        # Signal that this feature is not implemented on the current platform
        self.interface.factory.not_implemented("webview.cookies")

        return result

    def evaluate_javascript(self, javascript, on_result=None):
        # Construct a future on the event loop
        result = JavaScriptResult(on_result)

        # Define a callback that will update the future when
        # the Javascript is complete.
        def gtk_js_finished(webview, task, *user_data):
            """If `evaluate_javascript_finish` from GTK returns a result, unmarshal it,
            and call back with the result."""
            try:
                value = webview.evaluate_javascript_finish(task)
                if value.is_boolean():
                    value = value.to_boolean()
                elif value.is_number():
                    value = value.to_double()
                else:
                    value = value.to_string()

                result.set_result(value)
            except Exception as e:
                exc = RuntimeError(str(e))
                result.set_exception(exc)

        # Invoke the javascript method, with a callback that will set
        # the future when a result is available.
        self.native.evaluate_javascript(
            script=javascript,
            length=len(javascript),
            world_name=None,
            source_uri=None,
            cancellable=None,
            callback=gtk_js_finished,
        )

        # wait for the future, and return the result
        return result

    def rehint(self):
        self.interface.intrinsic.width = at_least(self.interface._MIN_WIDTH)
        self.interface.intrinsic.height = at_least(self.interface._MIN_HEIGHT)
