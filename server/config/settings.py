
import psycopg2
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    user: str
    password: str
    host: str
    port: int
    dbname: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def connection(self):
        try:
            conn = psycopg2.connect(
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
                dbname=self.dbname
            )
            # print("Database connected!")  # Optional
            return conn
        except Exception as e:
            print(f"Database connection failed: {e}")
            return None


settings = Settings()
