-- ============================================================
-- init.sql —— 智慧交通综合管理服务平台 建库建表脚本
-- 库：smart_traffic（utf8mb4_general_ci）
-- 约定：
--   1. 所有表含 id（自增主键）、created_at、updated_at；软删除用 is_deleted
--   2. 时间字段一律 DATETIME，存 Asia/Shanghai 本地时间，禁止 UTC 混用
--   3. 业务数据禁止物理 DELETE，统一软删除
--   4. 表间仅建逻辑外键（应用层保证一致性），不设物理外键约束，便于种子导入与软删除
-- ============================================================

CREATE DATABASE IF NOT EXISTS smart_traffic DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE smart_traffic;

-- ----------------------------
-- 1. 角色表
-- ----------------------------
DROP TABLE IF EXISTS role;
CREATE TABLE role (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  code        VARCHAR(32)  NOT NULL COMMENT '角色编码：admin/officer/user',
  name        VARCHAR(64)  NOT NULL COMMENT '角色名称',
  description VARCHAR(255) NOT NULL DEFAULT '' COMMENT '角色描述',
  is_deleted  TINYINT      NOT NULL DEFAULT 0 COMMENT '软删除：1已删',
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  UNIQUE KEY uk_role_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='角色表';

-- ----------------------------
-- 2. 用户表
-- ----------------------------
DROP TABLE IF EXISTS user;
CREATE TABLE user (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  username      VARCHAR(64)  NOT NULL COMMENT '登录名',
  password_hash VARCHAR(128) NOT NULL COMMENT 'bcrypt 密码哈希',
  real_name     VARCHAR(64)  NOT NULL DEFAULT '' COMMENT '姓名',
  phone         VARCHAR(20)  NOT NULL DEFAULT '' COMMENT '手机号',
  email         VARCHAR(128) NOT NULL DEFAULT '' COMMENT '邮箱',
  status        TINYINT      NOT NULL DEFAULT 1 COMMENT '1启用 0禁用',
  is_deleted    TINYINT      NOT NULL DEFAULT 0 COMMENT '软删除：1已删',
  created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  UNIQUE KEY uk_user_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='用户表';

-- ----------------------------
-- 3. 菜单表（角色-菜单-权限三级中的菜单级）
-- ----------------------------
DROP TABLE IF EXISTS menu;
CREATE TABLE menu (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  parent_id  INT         NOT NULL DEFAULT 0 COMMENT '父菜单 id，0=顶级',
  name       VARCHAR(64) NOT NULL COMMENT '菜单名称',
  path       VARCHAR(128) NOT NULL DEFAULT '' COMMENT '前端路由路径',
  component  VARCHAR(128) NOT NULL DEFAULT '' COMMENT '前端组件路径',
  icon       VARCHAR(64) NOT NULL DEFAULT '' COMMENT '图标名（Element Plus 图标）',
  menu_type  TINYINT     NOT NULL DEFAULT 1 COMMENT '1菜单 0目录',
  sort_order INT         NOT NULL DEFAULT 0 COMMENT '排序号',
  visible    TINYINT     NOT NULL DEFAULT 1 COMMENT '1显示 0隐藏',
  is_deleted TINYINT     NOT NULL DEFAULT 0 COMMENT '软删除：1已删',
  created_at DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='菜单表';

-- ----------------------------
-- 4. 用户-角色关联表
-- ----------------------------
DROP TABLE IF EXISTS user_role;
CREATE TABLE user_role (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT     NOT NULL COMMENT '用户 id',
  role_id    INT     NOT NULL COMMENT '角色 id',
  is_deleted TINYINT NOT NULL DEFAULT 0 COMMENT '软删除：1已删',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  UNIQUE KEY uk_user_role (user_id, role_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='用户-角色关联表';

-- ----------------------------
-- 5. 角色-菜单关联表
-- ----------------------------
DROP TABLE IF EXISTS role_menu;
CREATE TABLE role_menu (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  role_id    INT     NOT NULL COMMENT '角色 id',
  menu_id    INT     NOT NULL COMMENT '菜单 id',
  is_deleted TINYINT NOT NULL DEFAULT 0 COMMENT '软删除：1已删',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  UNIQUE KEY uk_role_menu (role_id, menu_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='角色-菜单关联表';

-- ----------------------------
-- 6. 路口表
-- ----------------------------
DROP TABLE IF EXISTS intersection;
CREATE TABLE intersection (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(64)    NOT NULL COMMENT '路口名称',
  longitude   DECIMAL(10,6)  NOT NULL COMMENT '经度',
  latitude    DECIMAL(10,6)  NOT NULL COMMENT '纬度',
  lane_count  INT            NOT NULL DEFAULT 4 COMMENT '车道数',
  district    VARCHAR(64)    NOT NULL DEFAULT '' COMMENT '所属辖区',
  status      TINYINT        NOT NULL DEFAULT 1 COMMENT '1启用 0停用',
  is_deleted  TINYINT        NOT NULL DEFAULT 0 COMMENT '软删除：1已删',
  created_at  DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at  DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  KEY idx_intersection_district (district)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='路口表';

-- ----------------------------
-- 7. 信号灯配时方案表
-- ----------------------------
DROP TABLE IF EXISTS signal_plan;
CREATE TABLE signal_plan (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  intersection_id INT          NOT NULL COMMENT '路口 id',
  name            VARCHAR(64)  NOT NULL COMMENT '方案名称',
  mode            VARCHAR(16)  NOT NULL DEFAULT 'fixed' COMMENT 'fixed=定周期 adaptive=感应自适应',
  cycle_seconds   INT          NOT NULL DEFAULT 90 COMMENT '周期时长（秒）',
  phase_count     INT          NOT NULL DEFAULT 4 COMMENT '相位数',
  phases          JSON         NULL COMMENT '相位配置 [{name,green,yellow,allRed}]',
  green_ratio     DECIMAL(5,4) NOT NULL DEFAULT 0.4000 COMMENT '绿信比=绿灯总时长/周期',
  is_active       TINYINT      NOT NULL DEFAULT 0 COMMENT '1=当前启用方案',
  created_by      INT          NULL COMMENT '创建人用户 id',
  is_deleted      TINYINT      NOT NULL DEFAULT 0 COMMENT '软删除：1已删',
  created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  KEY idx_plan_intersection (intersection_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='信号灯配时方案表';

-- ----------------------------
-- 8. 信号灯实时状态表（供大屏轮询）
-- ----------------------------
DROP TABLE IF EXISTS signal_status;
CREATE TABLE signal_status (
  id                INT AUTO_INCREMENT PRIMARY KEY,
  intersection_id   INT         NOT NULL COMMENT '路口 id',
  current_phase     VARCHAR(64) NOT NULL DEFAULT '' COMMENT '当前相位名',
  remaining_seconds INT         NOT NULL DEFAULT 0 COMMENT '剩余秒数',
  mode              VARCHAR(16) NOT NULL DEFAULT 'fixed' COMMENT '当前模式',
  cycle_seconds     INT         NOT NULL DEFAULT 90 COMMENT '当前周期（秒）',
  updated_at        DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  is_deleted        TINYINT     NOT NULL DEFAULT 0 COMMENT '软删除：1已删',
  created_at        DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  UNIQUE KEY uk_status_intersection (intersection_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='信号灯实时状态表';

-- ----------------------------
-- 9. 路段表
-- ----------------------------
DROP TABLE IF EXISTS road_section;
CREATE TABLE road_section (
  id                    INT AUTO_INCREMENT PRIMARY KEY,
  name                  VARCHAR(64)   NOT NULL COMMENT '路段名称',
  start_intersection_id INT           NOT NULL COMMENT '起点路口 id',
  end_intersection_id   INT           NOT NULL COMMENT '终点路口 id',
  lane_count            INT           NOT NULL DEFAULT 4 COMMENT '车道数',
  length_km             DECIMAL(6,2)  NOT NULL DEFAULT 1.00 COMMENT '长度（公里）',
  direction             VARCHAR(16)   NOT NULL DEFAULT '东西' COMMENT '走向：东西/南北',
  capacity              INT           NOT NULL DEFAULT 2400 COMMENT '通行能力 pcu/h（车道数×600）',
  is_deleted            TINYINT       NOT NULL DEFAULT 0 COMMENT '软删除：1已删',
  created_at            DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at            DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  KEY idx_section_start (start_intersection_id),
  KEY idx_section_end (end_intersection_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='路段表';

-- ----------------------------
-- 10. 交通流量表（小时聚合 + 分钟级实时上报共用；按天建索引）
-- ----------------------------
DROP TABLE IF EXISTS traffic_flow;
CREATE TABLE traffic_flow (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  road_section_id INT         NOT NULL COMMENT '路段 id',
  recorded_at     DATETIME    NOT NULL COMMENT '记录时间（本地时间）',
  flow            INT         NOT NULL DEFAULT 0 COMMENT '折算小时流率 pcu/h（分钟级=该分钟流量×60）',
  speed           DECIMAL(6,2) NOT NULL DEFAULT 0 COMMENT '平均车速 km/h',
  saturation      DECIMAL(5,3) NOT NULL DEFAULT 0 COMMENT '饱和度 v/c',
  congestion_level TINYINT    NOT NULL DEFAULT 0 COMMENT '0自由流 1缓行 2拥堵 3严重拥堵',
  is_deleted      TINYINT     NOT NULL DEFAULT 0 COMMENT '软删除：1已删',
  created_at      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  KEY idx_flow_section_time (road_section_id, recorded_at),
  KEY idx_flow_time (recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='交通流量表';

-- ----------------------------
-- 11. 车辆表
-- ----------------------------
DROP TABLE IF EXISTS vehicle;
CREATE TABLE vehicle (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  user_id     INT         NULL COMMENT '登记用户 id（普通用户本人车辆）',
  plate_no    VARCHAR(16) NOT NULL COMMENT '车牌号（含新能源 8 位）',
  vehicle_type VARCHAR(32) NOT NULL DEFAULT '小型汽车' COMMENT '车辆类型',
  color       VARCHAR(16) NOT NULL DEFAULT '' COMMENT '车身颜色',
  owner_name  VARCHAR(64) NOT NULL DEFAULT '' COMMENT '车主姓名',
  owner_phone VARCHAR(20) NOT NULL DEFAULT '' COMMENT '联系电话',
  is_deleted  TINYINT     NOT NULL DEFAULT 0 COMMENT '软删除：1已删',
  created_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  UNIQUE KEY uk_vehicle_plate (plate_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='车辆表';

-- ----------------------------
-- 12. 违章表
-- ----------------------------
DROP TABLE IF EXISTS violation;
CREATE TABLE violation (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  vehicle_id      INT          NULL COMMENT '车辆 id',
  plate_no        VARCHAR(16)  NOT NULL COMMENT '车牌号',
  intersection_id INT          NULL COMMENT '违章地点（路口 id）',
  violation_type  VARCHAR(32)  NOT NULL COMMENT '违章类型：闯红灯/超速/违停/不按导向车道行驶',
  violation_time  DATETIME     NOT NULL COMMENT '违章时间',
  fine_amount     DECIMAL(8,2) NOT NULL DEFAULT 0 COMMENT '罚款金额',
  deduct_points   INT          NOT NULL DEFAULT 0 COMMENT '扣分',
  status          VARCHAR(16)  NOT NULL DEFAULT 'pending' COMMENT 'pending待审核/confirmed已确认/rejected已驳回/processed已处理',
  evidence_url    VARCHAR(255) NOT NULL DEFAULT '' COMMENT '取证照片（/static/uploads 下相对路径）',
  audit_by        INT          NULL COMMENT '审核人用户 id',
  audit_remark    VARCHAR(255) NOT NULL DEFAULT '' COMMENT '审核备注',
  audit_time      DATETIME     NULL COMMENT '审核时间',
  remark          VARCHAR(255) NOT NULL DEFAULT '' COMMENT '备注',
  is_deleted      TINYINT      NOT NULL DEFAULT 0 COMMENT '软删除：1已删',
  created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  KEY idx_violation_plate (plate_no),
  KEY idx_violation_time (violation_time),
  KEY idx_violation_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='违章表';

-- ----------------------------
-- 13. 计费规则表
-- ----------------------------
DROP TABLE IF EXISTS fee_rule;
CREATE TABLE fee_rule (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  name           VARCHAR(64)  NOT NULL COMMENT '规则名称',
  free_minutes   INT          NOT NULL DEFAULT 15 COMMENT '免费时长（分钟）',
  first_hour_fee DECIMAL(8,2) NOT NULL DEFAULT 5.00 COMMENT '首小时费用（元）',
  hourly_fee     DECIMAL(8,2) NOT NULL DEFAULT 3.00 COMMENT '之后每小时费用（元，不足 1 小时按 1 小时）',
  daily_cap      DECIMAL(8,2) NOT NULL DEFAULT 40.00 COMMENT '单日封顶费用（元）',
  is_deleted     TINYINT      NOT NULL DEFAULT 0 COMMENT '软删除：1已删',
  created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='停车计费规则表';

-- ----------------------------
-- 14. 停车场表
-- ----------------------------
DROP TABLE IF EXISTS parking_lot;
CREATE TABLE parking_lot (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(64)  NOT NULL COMMENT '停车场名称',
  address     VARCHAR(255) NOT NULL DEFAULT '' COMMENT '地址',
  total_slots INT          NOT NULL DEFAULT 100 COMMENT '车位总数',
  used_slots  INT          NOT NULL DEFAULT 0 COMMENT '当前占用数',
  fee_rule_id INT          NULL COMMENT '计费规则 id',
  is_deleted  TINYINT      NOT NULL DEFAULT 0 COMMENT '软删除：1已删',
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='停车场表';

-- ----------------------------
-- 15. 出入场记录表
-- ----------------------------
DROP TABLE IF EXISTS parking_record;
CREATE TABLE parking_record (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  parking_lot_id INT          NOT NULL COMMENT '停车场 id',
  plate_no       VARCHAR(16)  NOT NULL COMMENT '车牌号',
  enter_time     DATETIME     NOT NULL COMMENT '入场时间',
  exit_time      DATETIME     NULL COMMENT '出场时间（空=在场）',
  fee            DECIMAL(8,2) NULL COMMENT '结算费用（元）',
  status         VARCHAR(16)  NOT NULL DEFAULT 'inside' COMMENT 'inside在场/finished已出场',
  image_url      VARCHAR(255) NOT NULL DEFAULT '' COMMENT '入场拍照（/static/uploads 下相对路径）',
  is_deleted     TINYINT      NOT NULL DEFAULT 0 COMMENT '软删除：1已删',
  created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  KEY idx_record_plate (plate_no),
  KEY idx_record_enter (enter_time),
  KEY idx_record_lot_status (parking_lot_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='出入场记录表';

-- ----------------------------
-- 16. 公告表
-- ----------------------------
DROP TABLE IF EXISTS notice;
CREATE TABLE notice (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  title        VARCHAR(128) NOT NULL COMMENT '公告标题',
  content      TEXT         NULL COMMENT '公告内容',
  publisher_id INT          NULL COMMENT '发布人用户 id',
  published_at DATETIME     NULL COMMENT '发布时间',
  status       TINYINT      NOT NULL DEFAULT 1 COMMENT '1已发布 0已下架',
  is_deleted   TINYINT      NOT NULL DEFAULT 0 COMMENT '软删除：1已删',
  created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  KEY idx_notice_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='公告表';

-- ----------------------------
-- 17. 投诉反馈表
-- ----------------------------
DROP TABLE IF EXISTS feedback;
CREATE TABLE feedback (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT          NOT NULL COMMENT '提交用户 id',
  title      VARCHAR(128) NOT NULL DEFAULT '' COMMENT '标题',
  content    TEXT         NOT NULL COMMENT '反馈内容',
  reply      TEXT         NULL COMMENT '处理答复',
  status     VARCHAR(16)  NOT NULL DEFAULT 'pending' COMMENT 'pending待受理/processing处理中/resolved已办结',
  handler_id INT          NULL COMMENT '受理人用户 id',
  handled_at DATETIME     NULL COMMENT '最近处理时间',
  is_deleted TINYINT      NOT NULL DEFAULT 0 COMMENT '软删除：1已删',
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  KEY idx_feedback_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='投诉反馈表';

-- ----------------------------
-- 18. 操作日志表
-- ----------------------------
DROP TABLE IF EXISTS op_log;
CREATE TABLE op_log (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT          NULL COMMENT '操作人用户 id',
  username   VARCHAR(64)  NOT NULL DEFAULT '' COMMENT '操作人用户名',
  action     VARCHAR(64)  NOT NULL COMMENT '操作类型：登录/新增/修改/删除/审核/发布等',
  detail     VARCHAR(512) NOT NULL DEFAULT '' COMMENT '操作详情',
  ip         VARCHAR(64)  NOT NULL DEFAULT '' COMMENT '来源 IP',
  is_deleted TINYINT      NOT NULL DEFAULT 0 COMMENT '软删除：1已删',
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  KEY idx_log_created (created_at),
  KEY idx_log_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='操作日志表';
