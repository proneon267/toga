import json
from http.cookiejar import CookieJar

from android.webkit import ValueCallback, WebView as A_WebView, WebViewClient
from java import dynamic_proxy
from java.util import Set

from toga.widgets.webview import CookiesResult, JavaScriptResult

try:
    from androidx.webkit import WebViewCompat
except ImportError:  # pragma: no cover
    # Import will fail if WebViewCompat is not listed in dependencies
    # No cover due to not being able to test in CI
    WebViewCompat = None

from .base import Widget


class ReceiveString(dynamic_proxy(ValueCallback)):
    def __init__(self, result):
        super().__init__()
        self.result = result

    def onReceiveValue(self, value):
        # If the evaluation fails, a message is written to Logcat, but the value sent to
        # the callback will be "null", with no way to distinguish it from an actual null
        # return value.
        res = json.loads(value)

        self.result.set_result(res)


if WebViewCompat is not None:  # pragma: no cover

    class ReceiveMessage(dynamic_proxy(WebViewCompat.WebMessageListener)):
        def __init__(self, webview):
            super().__init__()
            self.webview = webview

        def onPostMessage(self, view, message, sourceOrigin, isMainFrame, replyProxy):
            self.webview.interface.handle_js_msg(message.getData())


class WebView(Widget):
    SUPPORTS_ON_WEBVIEW_LOAD = False

    def create(self):
        self.native = A_WebView(self._native_activity)
        # Set a WebViewClient so that new links open in this activity,
        # rather than triggering the phone's web browser.
        self.native.setWebViewClient(WebViewClient())

        self.settings = self.native.getSettings()
        self.default_user_agent = self.settings.getUserAgentString()
        self.settings.setJavaScriptEnabled(True)
        self.settings.setDomStorageEnabled(True)
        # enable pinch-to-zoom without the deprecated on-screen controls
        self.settings.setBuiltInZoomControls(True)
        self.settings.setDisplayZoomControls(False)
        if WebViewCompat is None:  # pragma: no cover
            raise RuntimeError(
                "Unable to import WebViewCompat. Ensure that the AndroidX "
                "Webkit package (androidx.webkit:webkit:1.14.0) is listed in "
                "your app's dependencies."
            )
        WebViewCompat.addWebMessageListener(
            self.native,
            "WebviewMessageHandler",
            Set.of("*"),
            ReceiveMessage(self),
        )
        self.bridge_script = (
            """
            function receive_message(message) {
                handle_py_msg(message);
            }
            function send_message(message) {
                //console.log(webkit);
                WebviewMessageHandler.postMessage(message);
            }
            """
            + self.interface.handle_py_msg_script
        )
        self.native.evaluateJavascript(self.bridge_script, None)

    def send_message(self, message):
        self.native.evaluateJavascript(self.bridge_script, None)
        js_message = f"receive_message({json.dumps(message)});"
        self.native.evaluateJavascript(js_message, None)

    def get_url(self):
        url = self.native.getUrl()
        if url == "about:blank" or url.startswith("data:"):
            return None
        else:
            return url

    def set_url(self, value, future=None):
        if value is None:
            value = "about:blank"
        self.native.loadUrl(value)

        # Detecting when the load is complete requires subclassing WebViewClient
        # (https://github.com/beeware/toga/issues/1020).
        if future:
            future.set_result(None)

    def set_content(self, root_url, content):
        # There is a loadDataWithBaseURL method, but it's inconsistent about whether
        # getUrl returns the given URL or a data: URL. Rather than support this feature
        # intermittently, it's better to not support it at all.
        self.native.loadData(content, "text/html", "utf-8")

    def get_user_agent(self):
        return self.settings.getUserAgentString()

    def set_user_agent(self, value):
        self.settings.setUserAgentString(
            self.default_user_agent if value is None else value
        )

    def get_cookies(self):
        # Create the result object
        result = CookiesResult()
        result.set_result(CookieJar())

        # Signal that this feature is not implemented on the current platform
        self.interface.factory.not_implemented("webview.cookies")

        return result

    def evaluate_javascript(self, javascript, on_result=None):
        result = JavaScriptResult(on_result)

        self.native.evaluateJavascript(javascript, ReceiveString(result))
        return result
