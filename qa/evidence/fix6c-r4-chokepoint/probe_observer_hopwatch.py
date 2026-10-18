from types import SimpleNamespace as NS
from autotester.browser.observe import PageObserver, response_observer
from autotester.browser.role_probe import HopWatch, ResponseLog
class Ctx:
    def __init__(s): s.ev=[]
    def on(s,e,h): s.ev.append(("ctx",e))
class Page:
    def __init__(s): s.ev=[]; s.context=Ctx(); s.main_frame="mf"; s.log=[]
    def on(s,e,h): s.ev.append(e)
    def remove_listener(s,e,h): s.log.append(("rm",e))
    def route(s,p,h): s.log.append(("route",p))
    def unroute(s,p,h): s.log.append(("unroute",p))
    def goto(s,u): s.log.append(("goto",u))
# default observer registers the same 5 hooks as before
o=PageObserver(); p=Page(); o.attach(p); print("default", p.ev, p.context.ev)
# passive
po=PageObserver(passive=True); p2=Page(); po.attach(p2); print("passive", p2.ev, p2.context.ev)
# session without observer
sess=NS(page=Page(), observer=None)
hw=HopWatch(sess, lambda u: "evil" in u); hw.attach()
ob=sess.observer; print("hooks after attach", len(ob._hooks), sess.page.ev)
resp=NS(status=200,url="http://a/",request=NS(is_navigation_request=lambda:True, frame="mf", method="GET"), headers={})
ob._on_response(resp); print("status via hook", hw.status, "kept", ob.responses, ob.failed)
hw.detach(); print("hooks after detach", len(ob._hooks), sess.page.log)
hw.park(); print(sess.page.log[-1])
# real observer shared with ResponseLog and HopWatch, unsubscribe leaves ResponseLog
sess2=NS(page=Page(), observer=PageObserver()); sess2.observer.attach(sess2.page)
rl=ResponseLog(); rl.attach(sess2); hw2=HopWatch(sess2, lambda u: False); hw2.attach(); print("n hooks", len(sess2.observer._hooks), "response listeners on page", sess2.page.ev.count("response"))
hw2.detach(); print("after detach", len(sess2.observer._hooks))
# outside predicate preserved + guard aborts outside first hop
aborted=[]
route=NS(abort=lambda: aborted.append(1), continue_=lambda: aborted.append("c"))
req=NS(is_navigation_request=lambda:True, frame="mf", url="http://evil/x")
hw3=HopWatch(sess2, lambda u: "evil" in u); hw3._guard(route, req); print("guard", aborted)
