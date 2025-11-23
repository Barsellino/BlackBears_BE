from fastapi import APIRouter
from services.topics_service import TopicsService

router = APIRouter(prefix="/topics")

@router.get("/")
def all_topics():
    topics = TopicsService.get_all_topics()
    return [
        {
            "id": t["id"],
            "name": t["name"]
        }
        for t in topics
    ]

@router.get("/{topic_id}")
def get_topic(topic_id: str):
    topic = TopicsService.get_by_id(topic_id)
    if not topic:
        return {"error": "Topic not found"}
    return topic
