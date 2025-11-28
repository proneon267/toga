##########################################################################
# System/Library/Frameworks/WebKit.framework
##########################################################################
from ctypes import cdll, util

from rubicon.objc import ObjCClass, ObjCProtocol

######################################################################
webkit = cdll.LoadLibrary(util.find_library("WebKit"))
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
