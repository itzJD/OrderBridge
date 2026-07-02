import os
import sys
import threading

import servicemanager
import win32event
import win32service
import win32serviceutil


class OrderBridgeService(win32serviceutil.ServiceFramework):
    _svc_name_ = "OrderBridge"
    _svc_display_name_ = "OrderBridge Local Service"
    _svc_description_ = "Servicio local para sincronizar ordenes de GoodBarber, generar PDF e imprimir pedidos."

    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.server = None
        self.server_thread = None
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)

        servicemanager.LogInfoMsg("OrderBridge stopping...")

        if self.server is not None:
            self.server.should_exit = True

        win32event.SetEvent(self.stop_event)

        self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    def SvcDoRun(self):
        servicemanager.LogInfoMsg("OrderBridge starting...")

        os.chdir(self.base_dir)

        if self.base_dir not in sys.path:
            sys.path.insert(0, self.base_dir)

        self.ReportServiceStatus(win32service.SERVICE_RUNNING)

        self.server_thread = threading.Thread(target=self.run_server, daemon=True)
        self.server_thread.start()

        win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)

    def run_server(self):
        try:
            import uvicorn

            config = uvicorn.Config(
                "app.main:app",
                host="127.0.0.1",
                port=8000,
                log_level="info",
            )

            self.server = uvicorn.Server(config)
            self.server.run()

        except Exception as error:
            log_dir = os.path.join(self.base_dir, "logs")
            os.makedirs(log_dir, exist_ok=True)

            error_log = os.path.join(log_dir, "service-error.log")

            with open(error_log, "a", encoding="utf-8") as file:
                file.write(f"\nOrderBridge service error: {repr(error)}\n")

            servicemanager.LogErrorMsg(f"OrderBridge service error: {repr(error)}")


if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(OrderBridgeService)