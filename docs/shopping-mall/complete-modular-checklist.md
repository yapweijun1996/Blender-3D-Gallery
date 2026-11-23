# Shopping Mall — Complete Modular Checklist

This is the detailed planning checklist requested for building a complete virtual shopping mall, organized for item-by-item scoping. It covers reusable models, assembled spaces and application interactions; it is **not** a count of unique GLBs or a claim that the items are missing. Proposed P0/P1/P2 labels guide sequencing only and do not overwrite priorities in the [source 400-model backlog](production-backlog-v1.md) or the earlier 50-item request.

**Checkbox semantics:** unchecked means this checklist item has not yet been reconciled and accepted against its own requirements; it does not mean no existing asset exists. Many entries deliberately overlap across general and shop-specific sections. Reuse the same approved asset where suitable instead of building duplicates. Map each selected item to existing catalog IDs and, where applicable, `MALL-*` IDs before production; this checklist creates no competing canonical IDs. A shop is an assembled scene made from reusable modules, not necessarily one merged GLB. Interactions and animations are separate application deliverables.

**Brand and safety:** Watsons, Nitori and FairPrice are named as style/use-case references. Start with fictional branding; verify rights before using actual trademarks, signage or packaging. Safety and accessibility items are visual concepts, not certification of a real facility. Review cultural context separately for each festive design.

**Current project evidence:** See the [reconciliation notes](README.md), [P0 asset inventory](../gallery-p0-asset-inventory-2026-11-14.md), actual catalog, and [corridor preview](../../mall-modules-preview/). Existing GLBs require item-specific dimensions, pivot, interface, rights, source and validation checks before acceptance. Existing floor/ceiling pitch is 1.2 m; verify transitions against the source backlog's provisional 2 m dimensions.

**Per-item workflow:** (1) map to a backlog ID and inspect current candidates; (2) choose reuse/adapt/new and agree on dimensions, origin and connectors; (3) retain editable source, GLB, preview, metadata and rights; (4) verify the actual export, visual fit and performance, plus interaction/animation where requested; (5) mark accepted only with evidence. Choose LOD and target-device budgets per use rather than assuming all variants exist.

## A. Architecture and circulation

### 01. 建筑结构（P0）

- [ ] 直线地板模块 — 现有 [地板 GLB](../../models/mall-floor-tile/README.md)可复用；已与新墙做有限范围的高度与边界检查，完整场景及设备验收待确认。
- [ ] 转角地板模块 — 已用现有方形地板验证 L 形摆放；[方形外角收口盖](../../models/mall-floor-corner-trim/README.md)已通过单一 90° 接缝样本检查。现已新增 [1.2 m 外角地板](../../models/mall-floor-corner-tile/README.md) 和 [45° 斜接边条](../../models/mall-floor-mitred-trim/README.md)，并检查一个 90° 拼接样本；其他角型、完整装配及 2 m 规划规格仍待确认。
- [ ] 地板边缘收口 — 已创建 [1.2 m 直线收口条](../../models/mall-floor-edge-trim/README.md)和 [90° 外角盖](../../models/mall-floor-corner-trim/README.md)并进行本地检查；完整拼装及目标设备验收待完成。
- [ ] 地板过渡条
- [ ] 中庭边缘地板
- [ ] 架高平台
- [ ] 直线实体墙 — 本地已有 [1.2 m 墙模块](../../models/mall-solid-wall/README.md)及初步验证；代表性完整拼装、设备性能和 400 项计划的 2 m 规格对照仍待确认。
- [ ] 转角实体墙 — 已创建 [1.2 m 双臂墙角](../../models/mall-wall-corner/README.md)，并与两块直墙验证单一 90° 接口；完整拼装和 2 m 规划规格仍待验收。
- [ ] 墙壁端头
- [ ] 半高墙
- [ ] 玻璃隔墙
- [ ] 玻璃幕墙
- [ ] 墙面踢脚线
- [ ] 方形建筑柱
- [ ] 圆形建筑柱
- [ ] 柱子装饰包边
- [ ] 建筑横梁
- [ ] 中庭楼板边缘
- [ ] 室内拱门
- [ ] 室内入口门洞

### 02. 地面材质与装饰（P0/P1）

- [ ] 普通瓷砖地面
- [ ] 水磨石地面
- [ ] 大理石地面
- [ ] 木纹地板
- [ ] 地毯地砖
- [ ] 防滑地板
- [ ] 地面装饰镶边
- [ ] 地面方向箭头
- [ ] 盲道模块
- [ ] 门口地垫
- [ ] 中庭装饰地面图案
- [ ] 地板排水盖

### 03. 天花板与照明（P0/P1）

- [ ] 标准天花板模块
- [ ] 天花板格栅
- [ ] 天花板边缘收口
- [ ] 柱子周边天花收口
- [ ] 吊顶层级模块
- [ ] 装饰天花板
- [ ] 天窗
- [ ] 空调出风口
- [ ] 空调回风口
- [ ] 天花板维修口
- [ ] 圆形嵌入式筒灯
- [ ] 方形嵌入式灯
- [ ] 线性天花灯
- [ ] 面板灯
- [ ] 轨道灯
- [ ] 商店展示射灯
- [ ] 吊灯
- [ ] 装饰灯带
- [ ] 中庭大型吊灯
- [ ] 停车场天花灯
- [ ] 紧急照明灯

### 04. 门、窗与围栏（P0/P1）

- [ ] 单开玻璃门
- [ ] 双开玻璃门
- [ ] 自动滑动门
- [ ] 商店门框
- [ ] 商店玻璃橱窗
- [ ] 店面竖框
- [ ] 店面横框
- [ ] 店铺卷帘门
- [ ] 门把手
- [ ] 商场入口门
- [ ] 服务通道门
- [ ] 紧急出口门
- [ ] 直线玻璃围栏
- [ ] 转角玻璃围栏
- [ ] 围栏立柱
- [ ] 金属扶手
- [ ] 楼梯扶手
- [ ] 儿童安全门

## B. Shared public spaces

### 05. 扶梯、电梯与楼梯（P0）

- [ ] 自动扶梯上行模块
- [ ] 自动扶梯下行模块
- [ ] 扶梯顶部平台
- [ ] 扶梯底部平台
- [ ] 扶梯侧板
- [ ] 扶梯扶手
- [ ] 扶梯入口提示牌
- [ ] 电梯门
- [ ] 电梯门框
- [ ] 电梯外呼叫按钮
- [ ] 电梯楼层指示器
- [ ] 电梯内部轿厢
- [ ] 电梯内部按钮面板
- [ ] 电梯内部扶手
- [ ] 直线楼梯
- [ ] 转角楼梯
- [ ] 楼梯中间平台
- [ ] 楼梯踏步
- [ ] 楼梯扶手
- [ ] 无障碍坡道

### 06. 座位与休息区（P0/P1）

- [ ] 商场长椅
- [ ] 双人座椅
- [ ] 单人座椅
- [ ] 圆形座椅
- [ ] 转角座椅
- [ ] 带花槽长椅
- [ ] 长沙发
- [ ] 单人沙发
- [ ] 沙发脚凳
- [ ] 圆形茶几
- [ ] 方形茶几
- [ ] 休息区边桌
- [ ] 餐椅
- [ ] 双人餐桌
- [ ] 四人餐桌
- [ ] 圆形餐桌
- [ ] 吧台椅
- [ ] 儿童餐椅
- [ ] 充电座位
- [ ] 轮椅停放位

### 07. 公共设施（P0/P1）

- [ ] 商场信息柜台
- [ ] 数字导览机
- [ ] 楼层目录牌
- [ ] 广告灯箱
- [ ] 数字广告屏
- [ ] 墙面海报框
- [ ] 自动售货机
- [ ] 饮水机
- [ ] 雨伞套袋机
- [ ] 直立垃圾桶
- [ ] 分类回收桶
- [ ] 餐盘回收站
- [ ] 排队围栏立柱
- [ ] 排队伸缩带
- [ ] 临时告示牌
- [ ] 失物招领柜台
- [ ] 婴儿车停放架
- [ ] 轮椅租借点
- [ ] 储物柜
- [ ] 包裹领取柜
- [ ] 自动提款机
- [ ] 自助缴费机
- [ ] 手机充电站
- [ ] 免费 Wi-Fi 标示牌

### 08. 标牌与导视（P0/P1）

- [ ] 楼层编号牌
- [ ] 吊挂方向指示牌
- [ ] 墙面方向指示牌
- [ ] 落地导向牌
- [ ] 店铺编号牌
- [ ] 店铺营业时间牌
- [ ] 商场平面图牌
- [ ] “你在这里”标记
- [ ] 厕所指示牌
- [ ] 电梯指示牌
- [ ] 扶梯方向牌
- [ ] 停车场指示牌
- [ ] 出口指示牌
- [ ] 紧急出口灯牌
- [ ] 无障碍指示牌
- [ ] 亲子室指示牌
- [ ] 祈祷室指示牌
- [ ] 美食广场指示牌
- [ ] 商场活动海报
- [ ] 商场促销横幅
- [ ] 可替换店铺招牌
- [ ] 电子楼层目录屏

## C. Restrooms and service spaces

### 09. 公共厕所（P1）

- [ ] 厕所入口外框
- [ ] 男厕入口标牌
- [ ] 女厕入口标牌
- [ ] 无障碍厕所入口标牌
- [ ] 厕所隔间墙板
- [ ] 厕所隔间门
- [ ] 隔间门锁
- [ ] 坐式马桶
- [ ] 蹲式马桶
- [ ] 小便斗
- [ ] 小便斗隔板
- [ ] 洗手盆
- [ ] 长条洗手台
- [ ] 水龙头
- [ ] 镜子
- [ ] 皂液器
- [ ] 烘手机
- [ ] 擦手纸机
- [ ] 卫生纸架
- [ ] 卫生用品回收桶
- [ ] 厕所垃圾桶
- [ ] 地漏
- [ ] 无障碍扶手
- [ ] 无障碍紧急求助按钮
- [ ] 无障碍厕所转身空间标记
- [ ] 保洁用品柜

### 10. 亲子室与其他服务空间（P1/P2）

- [ ] 婴儿换尿布台
- [ ] 婴儿护理台
- [ ] 哺乳室隔间
- [ ] 哺乳室座椅
- [ ] 亲子室洗手盆
- [ ] 奶瓶清洗台
- [ ] 婴儿车停放区
- [ ] 儿童游乐区入口
- [ ] 急救室门
- [ ] 急救床
- [ ] 急救柜
- [ ] 祈祷室入口
- [ ] 祈祷室鞋架
- [ ] 清洁储藏室门
- [ ] 员工休息室门
- [ ] 管理办公室门
- [ ] 商场保安室柜台

## D. Reusable retail modules

### 11. 商店外观与店铺单元（P0/P1）

- [ ] 标准小型店铺外壳
- [ ] 标准中型店铺外壳
- [ ] 大型店铺外壳
- [ ] 转角店铺外壳
- [ ] 开放式店铺入口
- [ ] 双门店铺入口
- [ ] 玻璃展示窗
- [ ] 店铺招牌底板
- [ ] 发光店铺招牌
- [ ] 店铺橱窗展示台
- [ ] 店铺入口防盗门架
- [ ] 店内墙面展示板
- [ ] 店内地板模块
- [ ] 店内天花模块
- [ ] 店铺收银区
- [ ] 店铺储藏室门
- [ ] 店铺后仓货架
- [ ] 促销摊位
- [ ] 中庭快闪店
- [ ] 小型零售 kiosk

### 12. 商店货架与展示（P0/P1）

- [ ] 靠墙展示架
- [ ] 中央双面货架
- [ ] 货架端架
- [ ] 玻璃展示柜
- [ ] 上锁玻璃柜
- [ ] 商品展示底座
- [ ] 阶梯展示台
- [ ] 墙面层板
- [ ] 洞洞板
- [ ] 洞洞板挂钩
- [ ] 商品挂架
- [ ] 衣服直线挂架
- [ ] 衣服圆形挂架
- [ ] 鞋子展示架
- [ ] 手袋展示架
- [ ] 珠宝托盘
- [ ] 手表展示座
- [ ] 香水展示台
- [x] [化妆品试用台](../../models/mall-cosmetics-tester-bar/README.md)
- [ ] 手机展示防盗座
- [ ] 电视展示墙
- [ ] 电子产品体验桌
- [ ] 商品价格牌
- [ ] 商品介绍牌
- [ ] 促销标签
- [ ] 商品展示灯

### 13. 收银与购物用品（P0/P1）

- [ ] 收银柜台
- [ ] 转角收银台
- [ ] POS 收银机
- [ ] 触控结账屏
- [ ] 条码扫描器
- [ ] 收据打印机
- [ ] 钱箱
- [ ] 信用卡支付终端
- [ ] 自助结账机
- [ ] 购物篮
- [ ] 购物推车
- [ ] 购物袋
- [ ] 礼品包装台
- [ ] 排队号码牌
- [ ] 排队隔离带

### 14. 通用商品与包装（P1）

- [ ] 商品纸盒
- [ ] 礼品盒
- [ ] 饮料罐
- [ ] 食品罐
- [ ] 玻璃瓶
- [ ] 塑料瓶
- [ ] 洗发水瓶
- [ ] 护肤品罐
- [ ] 香水瓶
- [ ] 零食包装袋
- [ ] 书本
- [ ] 笔记本
- [ ] 衣服折叠堆
- [ ] T 恤
- [ ] 外套
- [ ] 裤子
- [ ] 鞋盒
- [ ] 鞋子
- [ ] 手袋
- [ ] 手机
- [ ] 平板电脑
- [ ] 笔记本电脑
- [ ] 耳机
- [ ] 键盘
- [ ] 电脑显示器
- [ ] 玩具盒
- [ ] 毛绒玩具
- [ ] 床上用品包装

## E. Complete shops

### 15. 时尚、生活与美容店（P1）

- [ ] 服装店
- [ ] 男装店
- [ ] 女装店
- [ ] 童装店
- [ ] 鞋店
- [ ] 手袋店
- [ ] 珠宝店
- [ ] 手表店
- [ ] 眼镜店
- [ ] 运动用品店
- [ ] 美容护肤店
- [ ] 美妆店
- [x] [药妆店](../../mall-modules-preview/README.md#pharmacy-and-beauty-shop)（6 m 店型，含试色、取货和货架）
- [ ] 香水店
- [ ] 药房
- [ ] 便利店
- [ ] 礼品店
- [ ] 玩具店
- [ ] 文具店
- [ ] 书店
- [ ] 花店
- [ ] 手机配件店
- [ ] 宠物用品店

### 16. 重点店铺场景（P1）

- [ ] 美发沙龙
- [ ] 美甲店
- [ ] 美容院
- [ ] Watsons 风格药妆店
- [ ] Nitori 风格家居店
- [ ] 家具店
- [ ] 床垫店
- [ ] 床品店
- [ ] FairPrice 风格超市
- [ ] 迷你超市
- [x] [电脑店](../../mall-modules-preview/README.md#computer-shop)（含实物演示台与陈列柜）
- [ ] 手机店
- [ ] 电子产品店
- [x] [面包店](../../mall-modules-preview/README.md#bakery-shop)（取餐区与后方服务通道）
- [ ] 蛋糕店
- [ ] 咖啡店
- [ ] 餐厅
- [ ] 茶饮店

### 17. 美发沙龙专属模型（P1）

- [ ] 沙龙接待柜台
- [ ] 理发椅
- [ ] 洗头椅
- [ ] 洗头盆
- [ ] 理发镜
- [ ] 理发工具推车
- [ ] 吹风机
- [ ] 理发器
- [ ] 毛巾架
- [ ] 护发产品展示架
- [ ] 沙龙等候椅
- [ ] 沙龙价目表

### 18. 药妆店与超市专属模型（P1）

- [ ] 药妆店收银台
- [ ] 药妆店中岛货架
- [x] [化妆品试用品台](../../models/mall-cosmetics-tester-bar/README.md)（同一件 MALL-RET-020）
- [ ] 护肤品壁架
- [ ] 药品展示柜
- [ ] 超市入口闸门
- [ ] 蔬果展示台
- [ ] 冷藏柜
- [ ] 冷冻柜
- [ ] 饮料冰箱
- [ ] 生鲜展示柜
- [ ] 超市货架端架
- [ ] 面包货架
- [ ] 超市称重机
- [ ] 购物篮架
- [ ] 购物推车回收区
- [ ] 自助结账区
- [ ] 传统收银通道

### 19. 家居店与卧室展示（P1）

- [ ] 家居店展示架
- [ ] 家具展示平台
- [x] [客厅沙发](../../models/living-room-sofa/README.md) · [家居店实装](../../mall-modules-preview/README.md#home-furnishings-shop)
- [ ] 客厅茶几
- [ ] 电视柜
- [x] [家居店餐桌](../../models/round-dining-table/README.md) · [家居店实装](../../mall-modules-preview/README.md#home-furnishings-shop)
- [x] [家居店餐椅](../../models/plastic-dining-chair/README.md) · [家居店实装](../../mall-modules-preview/README.md#home-furnishings-shop)
- [ ] 办公桌
- [ ] 办公椅
- [ ] 床架
- [ ] 床垫
- [ ] 枕头
- [ ] 被子
- [x] [床头柜](../../models/bedside-table/README.md) · [家居店实装](../../mall-modules-preview/README.md#home-furnishings-shop)
- [ ] 衣柜
- [ ] 梳妆台
- [ ] 台灯
- [ ] 落地灯
- [ ] 地毯
- [ ] 家居装饰品
- [ ] 家居店样板房隔墙

### 20. 电脑店与电子店专属模型（P1）

- [ ] 电脑展示桌
- [ ] 笔记本电脑展示架
- [ ] 台式电脑主机
- [ ] 显示器
- [ ] 电脑店键盘
- [ ] 鼠标
- [ ] 耳机展示架
- [ ] 电脑配件墙
- [ ] 手机展示台
- [ ] 平板展示台
- [ ] 电子店电视展示墙
- [ ] 游戏机展示台
- [ ] 电子店收银柜台
- [ ] 产品信息牌
- [x] [产品防盗线](../../models/mall-product-security-tether/README.md)（配合笔电、展示桌）
- [ ] 维修服务柜台

### 21. 面包店与餐饮模型（P1）

- [ ] 面包店柜台
- [ ] 玻璃面包展示柜
- [ ] 面包展示架
- [ ] 面包托盘
- [x] [面包夹](../../models/mall-bakery-serving-tongs/README.md)
- [ ] 面包纸袋
- [ ] 面包篮
- [ ] 蛋糕冷藏柜
- [ ] 餐饮饮料冰箱
- [ ] 点餐菜单牌
- [ ] 餐饮收银机
- [ ] 咖啡机
- [ ] 咖啡磨豆机
- [ ] 饮料制作台
- [ ] 食阁档口柜台
- [ ] 餐盘
- [ ] 杯子
- [ ] 餐具收纳站
- [ ] 餐饮餐盘回收站
- [ ] 餐桌与餐椅组合
- [ ] 厨房入口门
- [ ] 外卖领取架

## F. Decoration and events

### 22. 植物与花卉（P1）

- [ ] 小型花盆
- [ ] 圆形花盆
- [ ] 长方形花槽
- [ ] 带座椅花槽
- [ ] 室内小树
- [ ] 室内棕榈树
- [ ] 观叶植物
- [ ] 悬挂植物
- [ ] 花束
- [ ] 花瓶
- [ ] 花卉展示架
- [ ] 花店包装台
- [ ] 植物墙
- [ ] 中庭大型花槽

### 23. 活动与季节装饰（P2）

- [ ] 气球
- [ ] 气球束
- [ ] 气球拱门
- [ ] 气球立柱
- [ ] 中庭活动舞台
- [ ] 活动背景板
- [ ] 展览展板
- [ ] 快闪摊位
- [ ] 促销活动桌
- [ ] 商场横幅
- [ ] 节庆吊饰
- [ ] 圣诞树
- [ ] 圣诞礼盒
- [ ] 新年装饰灯笼
- [ ] 开斋节装饰
- [ ] 屠妖节灯饰
- [ ] 中秋节灯笼
- [ ] 拍照打卡背景
- [ ] 拍照框
- [ ] 儿童活动桌

## G. Parking and outdoors

### 24. 停车场结构（P1）

- [ ] 停车场地面模块
- [ ] 停车位线
- [ ] 普通停车位
- [ ] 无障碍停车位
- [ ] 亲子停车位
- [ ] 电动车停车位
- [ ] 摩托车停车位
- [ ] 自行车停车位
- [ ] 停车场柱子
- [ ] 柱子防撞护角
- [ ] 车轮挡块
- [ ] 减速带
- [ ] 停车场坡道
- [ ] 停车场入口
- [ ] 停车场出口
- [ ] 停车场天花管线
- [ ] 停车场通风口
- [ ] 排水沟盖
- [ ] 凸面镜
- [ ] 行人通道线

### 25. 停车收费与交通（P1/P2）

- [ ] 入口闸杆
- [ ] 出口闸杆
- [ ] 车牌识别摄像头
- [ ] 停车取票机
- [ ] 停车缴费机
- [ ] 停车场入口龙门架
- [ ] 停车场出口龙门架
- [ ] 车位空满指示灯
- [ ] 停车方向箭头
- [ ] 停车场楼层标志
- [ ] 停车收费说明牌
- [ ] 电动车充电桩
- [ ] 充电线和插头
- [ ] 防撞柱
- [ ] 交通锥
- [ ] 临时路障
- [ ] 自行车架
- [ ] 购物推车回收站

### 26. 商场室外环境（P1/P2）

- [ ] 商场主入口外立面
- [ ] 入口雨棚
- [ ] 室外招牌
- [ ] 户外广场地板
- [ ] 室外长椅
- [ ] 室外花槽
- [ ] 室外树木
- [ ] 路灯
- [ ] 人行道
- [ ] 路缘石
- [ ] 行人斑马线
- [ ] 落客区
- [ ] 出租车上落点
- [ ] 巴士站
- [ ] 交通指示牌
- [ ] 室外广告牌
- [ ] 室外垃圾桶
- [ ] 喷泉
- [ ] 景观水池
- [ ] 装卸区入口

## H. Safety, operations and interactions

### 27. 安全与维护（P1）

- [ ] 灭火器
- [ ] 灭火器挂架
- [ ] 消防水喉柜
- [ ] 手动火警按钮
- [ ] 烟雾探测器
- [ ] 洒水喷头
- [ ] 紧急出口推杆
- [ ] 急救箱
- [ ] AED 柜
- [ ] CCTV 半球摄像头
- [ ] CCTV 枪式摄像头
- [ ] 保安柜台
- [ ] 安检门
- [ ] 清洁推车
- [ ] 拖把桶
- [ ] 清洁警示牌
- [ ] 地板清洁机
- [ ] 电力配电箱
- [ ] 维修围栏
- [ ] 后勤垃圾回收箱

### 28. 人物与商场活动（P2）

- [ ] 普通顾客
- [ ] 推购物车顾客
- [ ] 带购物篮顾客
- [ ] 家长与儿童
- [ ] 轮椅使用者
- [ ] 商场服务人员
- [ ] 商店店员
- [ ] 收银员
- [ ] 保安人员
- [ ] 清洁人员
- [ ] 送货人员
- [ ] 坐着休息的顾客
- [ ] 排队顾客
- [ ] 理发师
- [ ] 沙龙顾客
- [ ] 面包店店员
- [ ] 餐饮店员
- [ ] 访客导览角色
- [ ] 待机动作
- [ ] 行走动作
- [ ] 坐下动作
- [ ] 挥手动作
- [ ] 推购物车动作

### 29. 可交互功能（按项目需要）

- [ ] 打开或关闭店门
- [ ] 打开或关闭卷帘门
- [ ] 使用电梯按钮
- [ ] 进入电梯
- [ ] 乘坐扶梯
- [ ] 点击导览机查看楼层
- [ ] 点击店铺招牌查看店铺资料
- [ ] 点击商品查看介绍
- [ ] 将商品放入购物篮
- [ ] 推动购物车
- [ ] 使用自助结账机
- [ ] 坐在长椅或沙发
- [ ] 查看广告屏内容
- [ ] 停车闸杆开启
- [ ] 切换日间和夜间照明
- [ ] 切换节庆装饰
- [ ] 在楼层之间导航

## Proposed production order

1. Building shell: floor, wall, column, ceiling, glazing and entrance; reconcile the module grid first.
2. First corridor: two shop units, doors, fascia and lighting, assembled with measured interfaces.
3. Public area: seating, planters, directory, waste bins and wayfinding.
4. First five assembled shops: pharmacy/beauty, computer, bakery, home furnishings and supermarket; use shared fixtures.
5. Vertical transport: escalators, lift and stairs.
6. Restrooms, accessible facilities and family rooms.
7. Parking, outdoor access and loading.
8. Merchandise, people, seasonal decoration and requested interactive features.

Each phase is planned; existing preview or checklist coverage is not proof that a phase has passed. Review the source plan's provisional dimensions and behavior-specific QA for each item. No publication, commit, or deployment is authorized by this checklist alone.
