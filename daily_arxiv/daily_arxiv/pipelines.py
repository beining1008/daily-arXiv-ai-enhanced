# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import arxiv
import json
import os
import sys
from datetime import datetime, timedelta
from scrapy.exceptions import DropItem


class DailyArxivPipeline:
    def __init__(self):
        self.page_size = 100
        self.client = arxiv.Client(self.page_size)
        # 从环境变量读取关键词配置 / Read keywords from environment variable
        keywords_env = os.environ.get("KEYWORDS", "")
        if keywords_env:
            # 分割关键词并转换为小写，去除空格 / Split keywords, convert to lowercase, strip spaces
            self.keywords = [k.strip().lower() for k in keywords_env.split(",") if k.strip()]
            self.logger_info = f"Keyword filtering enabled with {len(self.keywords)} keywords: {self.keywords}"
        else:
            self.keywords = []
            self.logger_info = "Keyword filtering disabled (no KEYWORDS environment variable set)"

    def open_spider(self, spider):
        """在爬虫开始时记录关键词过滤状态 / Log keyword filtering status when spider starts"""
        spider.logger.info(self.logger_info)

    def matches_keywords(self, title, summary):
        """
        检查标题和摘要是否包含目标关键词 / Check if title and summary contain target keywords

        Args:
            title (str): 论文标题 / Paper title
            summary (str): 论文摘要 / Paper summary

        Returns:
            bool: 如果没有设置关键词或匹配任一关键词则返回True / Returns True if no keywords set or matches any keyword
        """
        # 如果没有设置关键词，返回所有论文 / If no keywords set, return all papers
        if not self.keywords:
            return True

        # 将标题和摘要合并并转换为小写 / Combine title and summary and convert to lowercase
        text = (title + " " + summary).lower()

        # 检查是否包含任一关键词 / Check if contains any keyword
        return any(keyword in text for keyword in self.keywords)

    def process_item(self, item: dict, spider):
        item["pdf"] = f"https://arxiv.org/pdf/{item['id']}"
        item["abs"] = f"https://arxiv.org/abs/{item['id']}"
        search = arxiv.Search(
            id_list=[item["id"]],
        )
        paper = next(self.client.results(search))
        item["authors"] = [a.name for a in paper.authors]
        item["title"] = paper.title
        item["categories"] = paper.categories
        item["comment"] = paper.comment
        item["summary"] = paper.summary

        # 关键词过滤 / Keyword filtering
        if not self.matches_keywords(item["title"], item["summary"]):
            spider.logger.info(f"Dropped paper {item['id']} (title: {item['title'][:50]}...) - no keyword match")
            raise DropItem(f"Paper does not match keywords: {item['id']}")

        spider.logger.info(f"Accepted paper {item['id']} (title: {item['title'][:50]}...) - keyword match found")
        return item