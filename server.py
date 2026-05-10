#!/usr/bin/env python3
"""HackerNews MCP Server — Access HN stories, comments, and users for AI agents."""

import json, time
from mcp.server import Server, stdio_server
import httpx

server = Server("hackernews-mcp")
BASE_URL = "https://hacker-news.firebaseio.com/v0"

async def _get(path):
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{BASE_URL}/{path}")
        resp.raise_for_status()
        return resp.json()

def _format_story(item):
    return {
        "id": item.get("id"),
        "title": item.get("title", ""),
        "url": item.get("url", f"https://news.ycombinator.com/item?id={item['id']}"),
        "score": item.get("score", 0),
        "by": item.get("by", ""),
        "time": item.get("time", 0),
        "time_ago": f"{int((time.time() - item.get('time', time.time())) / 3600)}h ago",
        "descendants": item.get("descendants", 0),
        "type": item.get("type", "story"),
    }

@server.tool(
    name="get_top_stories",
    description="Get top stories from HackerNews right now",
    input_schema={
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Number of stories (max 30)", "default": 10}
        }
    }
)
async def get_top_stories(limit: int = 10) -> str:
    try:
        ids = await _get("topstories.json")
        results = []
        for sid in ids[:min(limit, 30)]:
            item = await _get(f"item/{sid}.json")
            if item and item.get("type") == "story":
                results.append(_format_story(item))
        return json.dumps({"stories": results, "source": "HackerNews"}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@server.tool(
    name="get_new_stories",
    description="Get newest stories from HackerNews",
    input_schema={
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Number of stories (max 30)", "default": 10}
        }
    }
)
async def get_new_stories(limit: int = 10) -> str:
    try:
        ids = await _get("newstories.json")
        results = []
        for sid in ids[:min(limit, 30)]:
            item = await _get(f"item/{sid}.json")
            if item and item.get("type") == "story":
                results.append(_format_story(item))
        return json.dumps({"stories": results}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@server.tool(
    name="get_best_stories",
    description="Get highest-rated stories from HackerNews",
    input_schema={
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Number of stories (max 30)", "default": 10}
        }
    }
)
async def get_best_stories(limit: int = 10) -> str:
    try:
        ids = await _get("beststories.json")
        results = []
        for sid in ids[:min(limit, 30)]:
            item = await _get(f"item/{sid}.json")
            if item and item.get("type") == "story":
                results.append(_format_story(item))
        return json.dumps({"stories": results}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@server.tool(
    name="get_story",
    description="Get full details of a HackerNews story or comment by ID",
    input_schema={
        "type": "object",
        "properties": {
            "story_id": {"type": "integer", "description": "HN story/item ID"}
        },
        "required": ["story_id"]
    }
)
async def get_story(story_id: int) -> str:
    try:
        item = await _get(f"item/{story_id}.json")
        if not item:
            return json.dumps({"error": f"Story {story_id} not found"})
        result = _format_story(item)
        result["text"] = item.get("text", "")
        # Get top-level comments
        kids = item.get("kids", [])[:5]
        comments = []
        for kid_id in kids:
            kid = await _get(f"item/{kid_id}.json")
            if kid:
                comments.append({
                    "id": kid["id"],
                    "by": kid.get("by", ""),
                    "text": kid.get("text", "")[:500],
                    "time": kid.get("time", 0),
                })
        result["comments"] = comments
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@server.tool(
    name="get_user",
    description="Get HackerNews user profile",
    input_schema={
        "type": "object",
        "properties": {
            "username": {"type": "string", "description": "HN username"}
        },
        "required": ["username"]
    }
)
async def get_user(username: str) -> str:
    try:
        user = await _get(f"user/{username}.json")
        if not user:
            return json.dumps({"error": f"User '{username}' not found"})
        return json.dumps({
            "username": user["id"],
            "created": user.get("created", 0),
            "karma": user.get("karma", 0),
            "about": user.get("about", ""),
            "submitted_count": len(user.get("submitted", [])),
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

def main():
    import anyio
    async def run():
        async with stdio_server() as streams:
            await server.run(streams[0], streams[1], server.create_initialization_options())
    anyio.run(run)

if __name__ == "__main__":
    main()
