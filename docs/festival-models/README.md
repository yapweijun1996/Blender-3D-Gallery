# Singapore and Malaysia Festival Models

Status: F01–F06 (Christmas tree, gift boxes, New Year clock, lion dance head,
kumquat tree and rabbit lantern) are implemented and locally verified. Several
later concepts already have models in the gallery; see the inventory update below.
A local result alone does not establish publication. The execution checklist
and order live in
[task.md](../../task.md#singapore-and-malaysia-festival-models--2026-11-15).

## Design direction

Create recognizable, original, individually viewable Blender models inspired by
festivals celebrated in Singapore and Malaysia. Favor clear silhouettes, rich
but restrained materials and details that remain readable in a small gallery
thumbnail. Design individual props so they can also be combined in future scenes.
The reference images below are AI-generated concept illustrations, not Blender
renders or specifications of exact cultural artifacts.

![Chinese New Year, Christmas and New Year concept board](new-year-christmas-concepts.png)

Top row, left to right: lion dance head, kumquat tree, Christmas tree. Bottom
row: presents, countdown clock, fireworks sculpture.

![Regional festival concept board](regional-festival-concepts.png)

Top row: Hari Raya ketupat and lamps, festive bazaar stall, Deepavali lamps and
flower design. Bottom row: Mid-Autumn lanterns and mooncakes, a generic harvest
basket, and a community celebration display. The harvest basket is only a visual
idea; it is not a verified representation of any specific community or festival.

## Existing gallery inventory

The following entries were found in [models/catalog.json](../../models/catalog.json)
on 2026-11-15. Catalog presence is not a fresh visual or quality assessment.

| Festival or theme | Existing model IDs |
| --- | --- |
| Christmas | `christmas-tree` (F01), `christmas-gift-boxes` (F02) |
| Gregorian New Year | `new-year-countdown-clock` (F03) |
| Chinese New Year | `chinese-new-year-kumquat-tree` (F05), `chinese-new-year-lion-dance-head` (F04), `chinese-new-year-lantern-arch`, `chinese-new-year-mandarin-orange-basket`, `chinese-new-year-red-packet-display` |
| Hari Raya | `hari-raya-ketupat-decoration`, `hari-raya-pelita-lamp`, `hari-raya-bazaar-stall` |
| Deepavali | `deepavali-oil-lamp`, `deepavali-kolam-floor-pattern`, `deepavali-festive-arch` |
| Mid-Autumn | `mid-autumn-lantern-display`, `mooncake-gift-box`, `mid-autumn-rabbit-lantern` (F06) |
| National Day | `national-day-flag-pole`, `singapore-flag-banner`, `malaysia-flag-banner` |

At the initial catalog inspection, no Christmas or Gregorian New Year model was
identified by name. F01–F03 add the Christmas tree, gift boxes and countdown
clock. Recheck the current catalog before creating each model to avoid
duplicates; the inventory may change.

### Reuse check on 2026-11-24

Four existing models cover parts of the later concept list. On this date, Chromium opened each public gallery viewer and loaded a GLB whose SHA-256 matched the local export.

| Concept | Existing geometry |
| --- | --- |
| Mid-Autumn mould tools | The [wooden mooncake mould workboard](../../models/wooden-mooncake-mould-workboard/README.md) contains a carved hand mould and a separate cake with the matching raised impression. |
| Christmas mall display | The [seasonal Christmas set](../../models/seasonal-christmas-decor/README.md) combines a decorated tree, four wrapped presents and two hanging snowflakes. The [Woodland Christmas Wreath](../../models/christmas-wreath/README.md) now supplies the separate hanging decoration. |
| Floral garlands | The [Deepavali lamps and rangoli set](../../models/deepavali-lamps-rangoli/README.md) includes two hanging marigold garlands. The [flower-garland stall](../../models/festival-flower-garland-stall/README.md) has additional retail stock and wrapping supplies. |

## Proposed model backlog

The rows below preserve the original proposals. The task tracker records delivery of F01–F06 and the standalone Christmas wreath. The reuse table above identifies portions covered by existing models.

| Theme | Proposed models | Design notes |
| --- | --- | --- |
| Christmas | Decorated Christmas tree; wrapped gift boxes; wreath; shopping-mall display | Start with a recognizable tree and gift boxes. Keep decorations separable in the source. |
| Gregorian New Year | Countdown clock; fireworks sculpture; celebratory balloon arch | Keep a clock readable and avoid permanently binding it to one year. Fireworks may begin as a static sculpture. |
| Chinese New Year | Lion dance head; kumquat tree; lion dance drum; reunion dinner table | Use existing lantern, orange and red-packet assets where appropriate instead of recreating them. |
| Hari Raya Aidilfitri | Traditional festive snack tray; open-house table setting; festive light display | Complement the existing ketupat, pelita and bazaar models. |
| Deepavali | Sweet box; flower garland; festive street-light display | Complement the existing lamp, kolam and arch models. |
| Mid-Autumn Festival | Tea set; mooncake-making tools | Complement the lantern display, mooncake box and rabbit lantern. |
| Singapore and Malaysia National Day | Community celebration stage; decorative bunting; festive light display | Treat country-specific designs separately and verify any national-symbol requirements before use. |
| Sabah Kaamatan | Harvest-themed display informed by Sabah references | Research the specific community, objects and context before design; do not treat a generic basket as an authentic artifact. |
| Sarawak Gawai | Harvest-themed display informed by Sarawak references | Research separately from Kaamatan and consult relevant sources or community input where feasible. |

For cultural context, see [Singapore Tourism Board on Mid-Autumn Festival](https://www.visitsingapore.com/content/visitsingapore/en/whats-happening/all-happenings/festivals/mid-autumn-festival/)
and [Tourism Malaysia's festival overview](https://ebrochures.malaysia.travel/en/malaysia-travel-guide/malaysia-the-ultimate-destination-for-special-interest-holiday/).
These sources establish context, not approval or detailed reference geometry.

## Per-model delivery and acceptance

Complete and verify one model before starting the next:

1. Check the current catalog for overlap; define the model's subject, intended
   appearance, reference sources and any cultural or rights questions.
2. Create original editable Blender source and export the real standalone GLB.
   Record attribution, rights, creation method and reproducibility information.
3. Produce a representative preview and register the model and metadata in the
   authoritative catalog using the existing `Festivals & Local Life` category.
4. Validate the actual GLB, dimensions and asset budgets against
   [the asset standard](../assets.md); run relevant asset validation and build.
5. Inspect the exported model and test its gallery card, loading, interactive
   viewer, controls, reset, error/accessibility fallback and responsive layout as
   applicable. Record evidence and unresolved limits before marking it complete.

Use existing gallery behavior: lightweight static cards and lazy 3D loading. Do
not claim an asset is interactive or production-ready until its actual export
and browser behavior have been verified. F01–F06 are locally verified;
publication requires separate confirmation.
