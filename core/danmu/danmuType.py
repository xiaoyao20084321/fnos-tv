import json
from dataclasses import dataclass, field
from typing import List


@dataclass
class DanMuType:
    text: str = ''  # 弹幕文本
    time: int = 0  # 弹幕时间
    mode: int = 1  # 弹幕模式
    color: str = '#FFFFFF'  # 弹幕颜色
    border: bool = False  # 弹幕是否有描边
    style: dict = field(default_factory=dict)  # 弹幕自定义样式
    other: dict = field(default_factory=dict)  # 其他数据

    def __dict__(self):
        if isinstance(self.color, str):
            self.color = self.color.replace('"', '')
        return dict(
            text=self.text.replace('&#', ''),
            time=int(self.time),
            mode=self.mode,
            color=str(self.color) if isinstance(self.color, str) and self.color.startswith(
                "#") else f'#{int(self.color):06X}',
            border=self.border,
            style=self.style
        )

    def escape_xml(self):
        # 定义需要转义的字符及其对应的转义序列
        escape_chars = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&apos;'
        }

        # 按照需要转义的字符顺序进行替换
        for char, escaped_char in escape_chars.items():
            self.text = self.text.replace(char, escaped_char)

        return self.text


@dataclass
class RetDanMuType:
    list: List[DanMuType]

    @property
    def xml(self) -> str:
        base_xml = '''<?xml version="1.0" encoding="utf-8"?>
<i>
{}
</i>'''
        return base_xml.format('\n'.join([self.list2xml(d) for d in self.list]))

    def list2xml(self, data: DanMuType):
        color = str(data.color) if isinstance(data.color, str) and data.color.startswith(
            "#") else f'#{int(data.color):06X}'
        xml_str = f'    <d p="{data.time},{data.mode},{data.style.get("size", 25)},{int(color[1:], 16) if isinstance(data.color, str) and data.color.startswith("#") else data.color},0,0,0,0">{data.escape_xml()}</d>'
        return xml_str
