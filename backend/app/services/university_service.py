"""
教育部高校名单验证服务
数据来源：教育部官方发布的《全国高等学校名单》
更新时间：2024年6月
覆盖范围：全国2711所普通高等学校（不含港澳台）
"""
import csv
import os
import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
from pathlib import Path

@dataclass
class UniversityInfo:
    """高校信息"""
    name: str  # 学校名称
    code: str  # 学校标识码
    department: str  # 主管部门
    location: str  # 所在地
    level: str  # 办学层次（本科/专科）
    is_private: bool  # 是否民办
    source: str = "教育部官方名单"  # 数据来源

@dataclass
class UniversityVerification:
    """高校验证结果"""
    is_verified: bool  # 是否通过验证
    university: Optional[UniversityInfo]  # 匹配的高校信息
    confidence: str  # 匹配度（high/medium/low）
    warnings: List[str]  # 警告信息
    source: str  # 数据来源说明


class UniversityService:
    """高校验证服务"""

    def __init__(self):
        self._universities: Dict[str, UniversityInfo] = {}
        self._aliases: Dict[str, str] = {}  # 别名映射
        self._data_loaded = False
        self._data_file = Path(__file__).parent.parent.parent / "data" / "china_universities.csv"

        # 常见的野鸡大学关键词（黑名单）
        self._fake_keywords = [
            "中国邮电大学",  # 虚假
            "中国工商管理大学",  # 虚假
            "北京工商管理大学",  # 虚假
            "上海经济贸易大学",  # 虚假
            "武汉工商管理大学",  # 虚假
        ]

    def _load_data(self):
        """加载高校数据"""
        if self._data_loaded:
            return

        if not self._data_file.exists():
            self._data_loaded = True
            return

        with open(self._data_file, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()

            # 找到表头行
            header_idx = -1
            for i, line in enumerate(lines):
                if '学校名称' in line and '学校标识码' in line:
                    header_idx = i
                    break

            if header_idx == -1:
                self._data_loaded = True
                return

            # 解析每一行数据
            for line in lines[header_idx + 1:]:
                line = line.strip()
                if not line:
                    continue

                # 解析CSV行（处理引号）
                parts = self._parse_csv_line(line)
                if len(parts) < 6:
                    continue

                school_name = parts[1].strip() if len(parts) > 1 else ''
                if not school_name or school_name == '学校名称':
                    continue

                # 跳过地区标题行（如"北京市（92所）"）
                if re.match(r'.*（\d+所）', school_name) or re.match(r'.*\(\d+schools?\)', school_name, re.IGNORECASE):
                    continue

                # 解析数据
                info = UniversityInfo(
                    name=school_name,
                    code=parts[2].strip() if len(parts) > 2 else '',
                    department=parts[3].strip() if len(parts) > 3 else '',
                    location=parts[4].strip() if len(parts) > 4 else '',
                    level=parts[5].strip() if len(parts) > 5 else '',
                    is_private=len(parts) > 6 and parts[6] and parts[6].strip() == '民办'
                )

                # 存储主名称
                self._universities[school_name] = info

                # 存储别名（括号内的简称）
                clean_name = school_name.replace('（', '').replace('）', '').replace('(', '').replace(')', '')
                if clean_name != school_name and clean_name:
                    self._aliases[clean_name] = school_name

                # 处理分校
                if '（' in school_name or '(' in school_name:
                    base_name = re.sub(r'[（(][^)）]*[)）]', '', school_name)
                    if base_name and base_name != school_name:
                        self._aliases[base_name] = school_name

        self._data_loaded = True

    def _parse_csv_line(self, line: str) -> list:
        """解析CSV行，处理引号"""
        parts = []
        current = []
        in_quotes = False

        for char in line:
            if char == '"':
                in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                parts.append(''.join(current))
                current = []
            else:
                current.append(char)

        if current:
            parts.append(''.join(current))

        return parts

    def verify(self, school_name: str) -> UniversityVerification:
        """
        验证高校是否为教育部承认的正规高校

        Args:
            school_name: 学校名称

        Returns:
            UniversityVerification: 验证结果
        """
        self._load_data()

        if not school_name or not school_name.strip():
            return UniversityVerification(
                is_verified=False,
                university=None,
                confidence="low",
                warnings=["学校名称为空"],
                source="教育部官方名单"
            )

        name = school_name.strip()
        warnings = []

        # 1. 精确匹配
        if name in self._universities:
            return UniversityVerification(
                is_verified=True,
                university=self._universities[name],
                confidence="high",
                warnings=[],
                source="教育部官方名单（精确匹配）"
            )

        # 2. 检查别名
        if name in self._aliases:
            real_name = self._aliases[name]
            return UniversityVerification(
                is_verified=True,
                university=self._universities[real_name],
                confidence="high",
                warnings=[f"学校名称 '{name}' 匹配到正规高校 '{real_name}'"],
                source="教育部官方名单（别名匹配）"
            )

        # 3. 模糊匹配
        for uni_name, uni_info in self._universities.items():
            if self._is_similar_name(name, uni_name):
                return UniversityVerification(
                    is_verified=True,
                    university=uni_info,
                    confidence="medium",
                    warnings=[f"学校名称 '{name}' 可能与正规高校 '{uni_name}' 相似，请确认"],
                    source="教育部官方名单（模糊匹配）"
                )

        # 4. 检查野鸡大学黑名单
        for fake_keyword in self._fake_keywords:
            if fake_keyword in name:
                return UniversityVerification(
                    is_verified=False,
                    university=None,
                    confidence="high",
                    warnings=[f"警告：'{name}' 包含已知虚假院校关键词 '{fake_keyword}'"],
                    source="教育部官方名单（黑名单）"
                )

        # 5. 检查是否可能是正规高校的变体
        suspicious = self._check_suspicious_name(name)
        if suspicious:
            return UniversityVerification(
                is_verified=False,
                university=None,
                confidence="medium",
                warnings=suspicious,
                source="教育部官方名单"
            )

        # 6. 未找到匹配（可能是海外高校或新成立高校）
        return UniversityVerification(
            is_verified=False,
            university=None,
            confidence="low",
            warnings=[
                f"在教育部2024年6月发布的《全国高等学校名单》中未找到 '{name}'",
                "可能原因：1) 海外高校；2) 新成立的高校；3) 成人高校（本名单不包含）；4) 虚假院校"
            ],
            source="教育部官方名单"
        )

    def _is_similar_name(self, name1: str, name2: str) -> bool:
        """判断两个学校名称是否相似"""
        # 移除括号内容后比较
        clean1 = re.sub(r'[（(][^)）]*[)）]', '', name1)
        clean2 = re.sub(r'[（(][^)）]*[)）]', '', name2)

        if clean1 == clean2:
            return True

        # 检查是否只是括号位置不同
        if clean1 in clean2 or clean2 in clean1:
            return True

        # 检查常见缩写
        abbreviations = {
            '北京理工大学': '北理工',
            '北京邮电大学': '北邮',
            '北京航空航天大学': '北航',
            '上海交通大学': '上海交大',
            '西安交通大学': '西安交大',
        }
        for full, abbr in abbreviations.items():
            if name1 == abbr and full in name2:
                return True
            if name2 == abbr and full in name1:

                return True

        return False

    def _check_suspicious_name(self, name: str) -> List[str]:
        """检查可疑的学校名称"""
        warnings = []

        # 检查是否与知名高校高度相似
        famous_unis = [
            '清华大学', '北京大学', '复旦大学', '上海交通大学',
            '浙江大学', '中国科学技术大学', '南京大学', '西安交通大学',
            '哈尔滨工业大学', '中国人民大学', '北京航空航天大学',
        ]

        for famous in famous_unis:
            if famous in name and name != famous:
                # 检查是否有轻微差异
                if len(name) - len(famous) <= 2:
                    warnings.append(f"警告：学校名称 '{name}' 与知名高校 '{famous}' 高度相似，可能是虚假院校")

        # 检查可疑后缀
        suspicious_suffixes = ['进修学院', '研修学院', '函授大学']
        for suffix in suspicious_suffixes:
            if name.endswith(suffix):
                warnings.append(f"注意：'{name}' 包含非正规学历后缀 '{suffix}'")

        return warnings

    def get_university_info(self, school_name: str) -> Optional[UniversityInfo]:
        """获取高校信息"""
        verification = self.verify(school_name)
        return verification.university

    def is_verified_university(self, school_name: str) -> bool:
        """快速检查是否为正规高校"""
        return self.verify(school_name).is_verified

    def get_all_universities(self) -> List[UniversityInfo]:
        """获取所有高校列表"""
        self._load_data()
        return list(self._universities.values())

    def get_universities_by_location(self, location: str) -> List[UniversityInfo]:
        """按地区获取高校列表"""
        self._load_data()
        return [u for u in self._universities.values() if location in u.location]

    def get_universities_by_level(self, level: str) -> List[UniversityInfo]:
        """按办学层次获取高校列表"""
        self._load_data()
        return [u for u in self._universities.values() if level in u.level]


# 全局单例
university_service = UniversityService()


def verify_school(school_name: str) -> UniversityVerification:
    """便捷函数：验证学校"""
    return university_service.verify(school_name)


def verify_schools(school_names: List[str]) -> Dict[str, UniversityVerification]:
    """批量验证学校"""
    return {name: university_service.verify(name) for name in school_names}
