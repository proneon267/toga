##########################################################################
# System/Library/Frameworks/WebKit.framework
##########################################################################

from rubicon.objc import ObjCClass, ObjCProtocol
from rubicon.objc.runtime import load_library

######################################################################
webkit = load_library("WebKit")
######################################################################

######################################################################
# WKWebView.h
WKWebView = ObjCClass("WKWebView")

######################################################################
# WKUserScript.h
WKUserScript = ObjCClass("WKUserScript")

######################################################################
# WKWebViewConfiguration.h
WKWebViewConfiguration = ObjCClass("WKWebViewConfiguration")
WKUserContentController = ObjCClass("WKUserContentController")

######################################################################
# WKFrameInfo.h
WKUIDelegate = ObjCProtocol("WKUIDelegate")
