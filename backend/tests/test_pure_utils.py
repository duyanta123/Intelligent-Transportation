# -*- coding: utf-8 -*-
"""服务层与工具层纯函数单元测试：菜单树构建、车牌校验、分页钳制、图片嗅探、时区归一化"""
from datetime import datetime

from app.models import Menu
from app.services.auth_service import build_menu_tree
from app.utils.validators import clamp_page, is_image_bytes, is_valid_plate, normalize_plate, to_local_naive


def _menu(mid: int, parent: int = 0, name: str = "", sort: int = 0) -> Menu:
    return Menu(id=mid, parent_id=parent, name=name or f"菜单{mid}", sort_order=sort)


class TestMenuTree:
    def test_build_two_level_tree(self):
        menus = [_menu(1, 0, "交通管理", 10), _menu(2, 1, "路口管理", 11), _menu(3, 1, "信号配时", 12)]
        tree = build_menu_tree(menus)
        assert len(tree) == 1
        root = tree[0]
        assert root["name"] == "交通管理"
        assert [c["name"] for c in root["children"]] == ["路口管理", "信号配时"]

    def test_sort_order_respected(self):
        menus = [_menu(1, 0, "B", 20), _menu(2, 0, "A", 10)]
        tree = build_menu_tree(menus)
        assert [n["name"] for n in tree] == ["A", "B"]

    def test_orphan_children_excluded_from_root(self):
        """父节点未在列表中时，子节点不会出现在顶层（防止菜单越权渲染）"""
        menus = [_menu(9, 123, "孤儿菜单")]
        assert build_menu_tree(menus) == []

    def test_empty_menu_list(self):
        assert build_menu_tree([]) == []


class TestPlateValidation:
    def test_normal_plates(self):
        assert is_valid_plate("京A12345")
        assert is_valid_plate("冀B6F888")

    def test_new_energy_plates(self):
        assert is_valid_plate("京AD12345")
        assert is_valid_plate("京AF8888")

    def test_invalid_plates(self):
        assert not is_valid_plate("BAD123")
        assert not is_valid_plate("京AI2345")  # 字母 I 不入发牌机关字母
        assert not is_valid_plate("京A123")
        assert not is_valid_plate("")

    def test_normalize_uppercases(self):
        assert normalize_plate(" jina12345 ") == normalize_plate("jina12345".upper())
        assert normalize_plate("京a12345") == "京A12345"


class TestClampPage:
    def test_clamp_bounds(self):
        assert clamp_page(0, 0) == (1, 10)  # size=0 回退默认 10
        assert clamp_page(-5, 1000) == (1, 100)
        assert clamp_page(3, 20) == (3, 20)


class TestClampPageMaxSize:
    def test_flow_history_allows_500(self):
        """流量历史接口声明的 size 上限是 500，clamp 不得静默截到 100"""
        assert clamp_page(1, 500, max_size=500) == (1, 500)
        assert clamp_page(1, 501, max_size=500) == (1, 500)

    def test_default_cap_unchanged(self):
        assert clamp_page(1, 500) == (1, 100)


class TestImageBytes:
    def test_jpeg_png_webp_headers(self):
        assert is_image_bytes(b"\xff\xd8\xff\xe0" + b"0" * 20)
        assert is_image_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 20)
        assert is_image_bytes(b"RIFF" + b"0" * 4 + b"WEBP" + b"0" * 20)

    def test_non_image_rejected(self):
        assert not is_image_bytes(b"<html>definitely not an image</html>")
        assert not is_image_bytes(b"short")


class TestToLocalNaive:
    def test_utc_input_converted_to_shanghai(self):
        """toISOString 传参（Z 结尾）必须归一化，否则查询窗口偏移 8 小时"""
        from datetime import timezone

        utc_dt = datetime(2026, 9, 20, 2, 0, 0, tzinfo=timezone.utc)
        assert to_local_naive(utc_dt) == datetime(2026, 9, 20, 10, 0, 0)

    def test_naive_passthrough_and_none(self):
        naive = datetime(2026, 9, 20, 8, 0, 0)
        assert to_local_naive(naive) == naive
        assert to_local_naive(None) is None
