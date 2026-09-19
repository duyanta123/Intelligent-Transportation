# -*- coding: utf-8 -*-
"""服务层与工具层纯函数单元测试：菜单树构建、车牌校验、分页钳制"""
from app.models import Menu
from app.services.auth_service import build_menu_tree
from app.utils.validators import clamp_page, is_valid_plate, normalize_plate


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
