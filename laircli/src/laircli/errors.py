"""CLI 错误 → 退出码：1=接口/业务失败，2=用法错误（由 typer 负责），3=未配置。"""


class CliError(Exception):
    exit_code = 1


class NotConfigured(CliError):
    exit_code = 3
