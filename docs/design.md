# Design and accessibility

Status: proposed direction; validate with real designs and browser testing.

The experience should prioritize artwork: a restrained visual gallery with clear search and category controls, consistent image proportions and a model detail view. Avoid administrative navigation and oversized introductory content that hides the collection. An initial dark graphite palette with a restrained accent is a candidate, not a final brand decision.

Use semantic design tokens for color, spacing, type and focus states. Size body text for mobile readability, support long titles and preserve image aspect ratios to reduce layout shifts. Candidate breakpoints range from one or two columns on phones to four on wide desktops; actual layouts must be checked at 320, 390, 768 and 1440 CSS pixels.

Gallery controls must be keyboard accessible and show active filters, focus, empty results and loading or image failures. Use descriptive alternative text and sufficiently large touch targets. The viewer should expose reset and help, support touch, respect reduced-motion preferences, and show an informative poster and text when 3D cannot load.

If PWA support is approved, specify the offline scope, safe-area behavior and update flow. A new version should be applied through a visible user-controlled action with loading and failure states. Do not call the site PWA-ready without testing installation, offline behavior and updates, including relevant real devices.
