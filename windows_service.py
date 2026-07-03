import os
import subprocess
import sys

import servicemanager
import win32event
import win32service
import win32serviceutil


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOOT_LOG = os.path.join(BASE_DIR, "logs", "service-boot.log")
VENV_PYTHON = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")


def boot_log(message: str) -> None:
    os.makedirs(os.path.dirname(BOOT_LOG), exist_ok=True)
    with open(BOOT_LOG, "a", encoding="utf-8") as file:
        file.write(f"{message}\n")


def get_settings():
    from app.config import settings

    return settings


boot_log("module import reached")


class OrderBridgeService(win32serviceutil.ServiceFramework):
    _svc_name_ = "OrderBridge"
    _svc_display_name_ = "OrderBridge Local Service"
    _svc_description_ = "Servicio local para sincronizar ordenes de GoodBarber, generar PDF e imprimir pedidos."

    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.server_process = None
        self.stdout_file = None
        self.stderr_file = None
        self.base_dir = BASE_DIR
        boot_log("service __init__ reached")

    def SvcStop(self):
        boot_log("SvcStop called")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)

        servicemanager.LogInfoMsg("OrderBridge stopping...")

        win32event.SetEvent(self.stop_event)

        if self.server_process is not None and self.server_process.poll() is None:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.server_process.kill()

        if self.stdout_file is not None:
            self.stdout_file.close()
            self.stdout_file = None

        if self.stderr_file is not None:
            self.stderr_file.close()
            self.stderr_file = None

        self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    def SvcDoRun(self):
        servicemanager.LogInfoMsg("OrderBridge starting...")
        boot_log("SvcDoRun entered")
        self.ReportServiceStatus(win32service.SERVICE_START_PENDING)

        os.chdir(self.base_dir)

        if self.base_dir not in sys.path:
            sys.path.insert(0, self.base_dir)

        self.server_process = self.start_uvicorn_process()
        boot_log("uvicorn subprocess started")

        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        try:
            while win32event.WaitForSingleObject(self.stop_event, 1000) != win32event.WAIT_OBJECT_0:
                if self.server_process is not None and self.server_process.poll() is not None:
                    servicemanager.LogErrorMsg(
                        f"OrderBridge uvicorn exited unexpectedly with code {self.server_process.returncode}"
                    )
                    break
        finally:
            if self.server_process is not None and self.server_process.poll() is None:
                self.server_process.terminate()
                try:
                    self.server_process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    self.server_process.kill()

    def start_uvicorn_process(self):
        try:
            log_dir = os.path.join(self.base_dir, "logs")
            os.makedirs(log_dir, exist_ok=True)

            stdout_path = os.path.join(log_dir, "uvicorn.out.log")
            stderr_path = os.path.join(log_dir, "uvicorn.err.log")

            self.stdout_file = open(stdout_path, "a", encoding="utf-8")
            self.stderr_file = open(stderr_path, "a", encoding="utf-8")

            command = [
                VENV_PYTHON,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                get_settings().api_host,
                "--port",
                str(get_settings().api_port),
            ]

            return subprocess.Popen(
                command,
                cwd=self.base_dir,
                stdout=self.stdout_file,
                stderr=self.stderr_file,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception as error:
            boot_log(f"start_uvicorn_process error: {repr(error)}")
            log_dir = os.path.join(self.base_dir, "logs")
            os.makedirs(log_dir, exist_ok=True)

            error_log = os.path.join(log_dir, "service-error.log")

            with open(error_log, "a", encoding="utf-8") as file:
                file.write(f"\nOrderBridge service error: {repr(error)}\n")

            servicemanager.LogErrorMsg(f"OrderBridge service error: {repr(error)}")
            raise


if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(OrderBridgeService)
