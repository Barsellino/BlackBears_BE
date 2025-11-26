import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "topics.json"


class TopicsService:
    _cache = None

    @classmethod
    def load_topics(cls):
        if cls._cache is not None:
            return cls._cache

        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        cls._cache = data 
        return data

    @classmethod
    def get_all_topics(cls):
        return cls.load_topics()["topics"]

    @classmethod
    def get_by_id(cls, topic_id: str):
        for t in cls.get_all_topics():
            if t["id"] == topic_id:
                return t
        return None