from apis.base import RequestBase

new_config = {
    "panews": {
        "headers": {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0",
        },
        "host": "https://universal-api.panewslab.com"
    },
    "marsbit": {
        "headers": {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0",
        },
        "host": "https://api.marsbit.co"
    }
}


class NewApi:
    # 处理日历
    CALENDAR_FORMATTER = lambda res: [
        {
            "create_at": item["createdAt"],
            "title": item.get("translations", {}).get("title"),
            "new_type": "calendar"
        }
        for item in res.json()
        if isinstance(item, dict)
    ]
    NEW_FORMATTER = lambda res: [
        {
            "create_at": item["createdTime"],
            "title":title_content[0] ,
            "content": title_content[1],
            "new_type": "new"
        }
        for item in res.json().get("obj",{}).get("inforList",[])
        if isinstance(item, dict)
           and
           (title_content := item.get("translations", {}).get("title", "").split("火星财经消息，"))
           and
           len(title_content)==2
    ]

    def __init__(self):
        # ?take=100&skip=0&startAt=between,2026-06-27T16:00:00.000Z,2026-08-08T15:59:59.999Z
        self.calendar = RequestBase(url=new_config["panews"]["host"] + "/calendar/events?take=100&skip=0&startAt=between,2026-06-27T16:00:00.000Z,2026-08-08T15:59:59.999Z",
                                    headers=new_config["panews"]["headers"],
                                    response_formatter=self.CALENDAR_FORMATTER
                                    )

        self.new = RequestBase(url=new_config["marsbit"]["host"] + "info/lives/showlives",
                               headers=new_config["marsbit"]["headers"],
                               response_formatter=self.NEW_FORMATTER)

_NewApi=NewApi()
