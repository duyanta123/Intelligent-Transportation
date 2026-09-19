"""全局配置：一律从 .env 读取，禁止硬编码密钥（见 AGENTS.md 安全红线）"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 数据库
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_NAME: str = "smart_traffic"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    # Redis
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    # JWT
    JWT_SECRET: str = "dev-secret-please-change"
    JWT_EXPIRE_MINUTES: int = 120
    # 业务开关与 TTL
    MOCK_DATA_ENABLED: bool = True
    CAPTCHA_TTL_SECONDS: int = 300
    DASHBOARD_CACHE_TTL_SECONDS: int = 8
    UPLOAD_DIR: str = "uploads"
    # 测试开关：pytest 下置 1，禁用定时任务与真实依赖混用
    TESTING: int = 0

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def db_url(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    @property
    def test_db_name(self) -> str:
        return self.DB_NAME + "_test"

    @property
    def test_db_url(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.test_db_name}?charset=utf8mb4"
        )

    @property
    def server_db_url(self) -> str:
        """不带库名的服务器连接串，用于测试库自动建库"""
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/?charset=utf8mb4"
        )


settings = Settings()
