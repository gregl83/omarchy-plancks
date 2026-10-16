# Animations

Choose a companion in **Settings → Animated graphic**. The choices appear in the order below, and each preview cycles through the same seven states.

These stills use the packaged notification assets, cropped and fitted individually to a square icon with a small transparent border. Their scale and placement differ from the fixed live animation canvas. Countdown rows read left to right at **25%, 50%, and 75% of the predicted interval elapsed**. Other rows show one representative frame; the descriptions explain motion that a still cannot show. The live graphic uses your theme color and is dimmed during off-time.

“Learning” means there is no prediction yet. Passing an expected end or start keeps the current phase until you end or start the epoch yourself.

- [Sun and moon](#sun-and-moon)
- [Coffee cup](#coffee-cup)
- [Starship](#starship)
- [Roadster](#roadster)

## Sun and moon

The sun represents an active epoch; the crescent moon represents off-time. Each descends behind a soft, nearly flat curved horizon as its predicted interval runs out. This follows your epochs, independently of actual daylight.

| State | Stills | Behavior |
| --- | --- | --- |
| Ready to start | <img src="../assets/notifications/sun-moon/off-time/fill-000.png" width="58" height="58" alt="Sun and moon: Ready to start"> | Sun peeking above the horizon, stationary. |
| Epoch · learning | <img src="../assets/notifications/sun-moon/learning/active.png" width="58" height="58" alt="Sun and moon: Epoch · learning"> | Sun at a fixed height with rotating rays; no predicted progress yet. |
| Epoch · countdown | <img src="../assets/notifications/sun-moon/active/fill-075.png" width="58" height="58" alt="Sun and moon: Epoch · countdown, 25% elapsed"> <img src="../assets/notifications/sun-moon/active/fill-050.png" width="58" height="58" alt="Sun and moon: Epoch · countdown, 50% elapsed"> <img src="../assets/notifications/sun-moon/active/fill-025.png" width="58" height="58" alt="Sun and moon: Epoch · countdown, 75% elapsed"> | Sun descends toward the horizon, with rotating rays. |
| Epoch · past expected end | <img src="../assets/notifications/sun-moon/overtime/active.png" width="58" height="58" alt="Sun and moon: Epoch · past expected end"> | Sun remains partly below the horizon; its rays gently pulse. |
| Off-time · learning | <img src="../assets/notifications/sun-moon/learning/off-time.png" width="58" height="58" alt="Sun and moon: Off-time · learning"> | Moon at a fixed height with three staggered, twinkling stars; no predicted progress yet. |
| Off-time · countdown | <img src="../assets/notifications/sun-moon/off-time/fill-025.png" width="58" height="58" alt="Sun and moon: Off-time · countdown, 25% elapsed"> <img src="../assets/notifications/sun-moon/off-time/fill-050.png" width="58" height="58" alt="Sun and moon: Off-time · countdown, 50% elapsed"> <img src="../assets/notifications/sun-moon/off-time/fill-075.png" width="58" height="58" alt="Sun and moon: Off-time · countdown, 75% elapsed"> | Moon descends toward the horizon as the stars fade. |
| Off-time · past expected start | <img src="../assets/notifications/sun-moon/overtime/off-time.png" width="58" height="58" alt="Sun and moon: Off-time · past expected start"> | Moon remains at the horizon with a gentle pulse. |

## Coffee cup

The liquid level represents the remaining epoch or the progress of off-time. The cup empties during an epoch and refills during off-time.

| State | Stills | Behavior |
| --- | --- | --- |
| Ready to start | <img src="../assets/notifications/coffee/off-time/fill-000.png" width="58" height="58" alt="Coffee cup: Ready to start"> | Empty cup. |
| Epoch · learning | <img src="../assets/notifications/coffee/learning/active.png" width="58" height="58" alt="Coffee cup: Epoch · learning"> | Empty cup with drifting steam; no predicted fill level yet. |
| Epoch · countdown | <img src="../assets/notifications/coffee/active/fill-075.png" width="58" height="58" alt="Coffee cup: Epoch · countdown, 25% elapsed"> <img src="../assets/notifications/coffee/active/fill-050.png" width="58" height="58" alt="Coffee cup: Epoch · countdown, 50% elapsed"> <img src="../assets/notifications/coffee/active/fill-025.png" width="58" height="58" alt="Coffee cup: Epoch · countdown, 75% elapsed"> | Liquid level falls toward empty. |
| Epoch · past expected end | <img src="../assets/notifications/coffee/overtime/active.png" width="58" height="58" alt="Coffee cup: Epoch · past expected end"> | Cup stays empty. |
| Off-time · learning | <img src="../assets/notifications/coffee/learning/off-time.png" width="58" height="58" alt="Coffee cup: Off-time · learning"> | Empty cup with drifting steam; no predicted fill level yet. |
| Off-time · countdown | <img src="../assets/notifications/coffee/off-time/fill-025.png" width="58" height="58" alt="Coffee cup: Off-time · countdown, 25% elapsed"> <img src="../assets/notifications/coffee/off-time/fill-050.png" width="58" height="58" alt="Coffee cup: Off-time · countdown, 50% elapsed"> <img src="../assets/notifications/coffee/off-time/fill-075.png" width="58" height="58" alt="Coffee cup: Off-time · countdown, 75% elapsed"> | Liquid level rises toward full. |
| Off-time · past expected start | <img src="../assets/notifications/coffee/overtime/off-time.png" width="58" height="58" alt="Coffee cup: Off-time · past expected start"> | Cup stays full. |

## Starship

The fuel tank drains during an active epoch and refills on the launch pad during off-time.

| State | Stills | Behavior |
| --- | --- | --- |
| Ready to start | <img src="../assets/notifications/starship/off-time/fill-000.png" width="58" height="58" alt="Starship: Ready to start"> | Empty tank on the launch pad. |
| Epoch · learning | <img src="../assets/notifications/starship/learning/active.png" width="58" height="58" alt="Starship: Epoch · learning"> | Flickering nozzle flame, without a predicted fuel level. |
| Epoch · countdown | <img src="../assets/notifications/starship/active/fill-075.png" width="58" height="58" alt="Starship: Epoch · countdown, 25% elapsed"> <img src="../assets/notifications/starship/active/fill-050.png" width="58" height="58" alt="Starship: Epoch · countdown, 50% elapsed"> <img src="../assets/notifications/starship/active/fill-025.png" width="58" height="58" alt="Starship: Epoch · countdown, 75% elapsed"> | Fuel drains while the nozzle flame flickers. |
| Epoch · past expected end | <img src="../assets/notifications/starship/overtime/active.png" width="58" height="58" alt="Starship: Epoch · past expected end"> | Empty tank with the flame off. |
| Off-time · learning | <img src="../assets/notifications/starship/learning/off-time.png" width="58" height="58" alt="Starship: Off-time · learning"> | Pulsing fuel connection on the launch pad, without a predicted fuel level. |
| Off-time · countdown | <img src="../assets/notifications/starship/off-time/fill-025.png" width="58" height="58" alt="Starship: Off-time · countdown, 25% elapsed"> <img src="../assets/notifications/starship/off-time/fill-050.png" width="58" height="58" alt="Starship: Off-time · countdown, 50% elapsed"> <img src="../assets/notifications/starship/off-time/fill-075.png" width="58" height="58" alt="Starship: Off-time · countdown, 75% elapsed"> | Fuel fills on the launch pad. |
| Off-time · past expected start | <img src="../assets/notifications/starship/overtime/off-time.png" width="58" height="58" alt="Starship: Off-time · past expected start"> | Full tank on the launch pad. |

## Roadster

Inspired by the low curved canopy, rounded rear shoulders, wide light bar, four rear nozzles, and active wing seen in Tesla’s October 15, 2026 reveal. The simplified silhouette follows the [reveal photo gallery](https://www.autoexpress.co.uk/tesla/roadster/370689/new-tesla-roadster-revealed-2026-pictures), keeping the sharp accents without tracing every body detail. The airborne motion references Tesla’s [kickflip](https://www.youtube.com/watch?v=r5vsHHPVhJg) and [ramp demonstration](https://www.youtube.com/watch?v=7p5LxFdc-Qg). The compact graphic rises gradually over the first 45% of the predicted epoch, stays high through the 45%–55% roll, and descends over the final 45% to land at the expected end. Takeoff and touchdown ease smoothly, with continuous jets that widen from each thruster to the ground, then billow outward from their impact points. Ground wash follows the displayed height, fades out as the car clears the ground, and returns during descent. Thrusters and ground wash continue through the landing ease, stopping only once the car rests on the ground; mid-flight vapor stays attached to the exhaust, with no ground wash. Offset pulses subtly vary each jet’s length, width, brightness, and plume contour, while soft vapor billows fluctuate independently. Ground-reaching jets keep their endpoints connected to the surface. It uses bright downward gas streams surrounded by a broad vapor cloud, and lateral jets during one rotation across **45%–55% of the predicted epoch**. Bottom exhaust tapers to short residual jets while the car is sideways or inverted; lateral jets carry the middle of the roll, and bottom thrust returns more aggressively as the car comes upright, with a brighter, longer catch plume that settles by 65% elapsed. Rotation advances at a constant rate with epoch progress: upright at 45%, upside down at 50%, and upright again at 55%. For a 13-hour epoch, the flip lasts 78 minutes, from 5h 51m to 7h 9m elapsed. Opening the panel immediately shows the current angle; Settings uses the same ratios in its accelerated cycle. The pitched rear wing has a broad blade and swept-down endplates below the roofline, with the underlying body lines masked and a narrow clear gap around its edges, above a deeper rear section, broad tires, and four small low-set nozzles. The ground fades out during takeoff and returns on landing.

The body fill is a symbolic reserve: it drains during an epoch and replenishes during off-time, matching Coffee cup and Starship. It does not simulate the vehicle’s battery, air pressure, or flight endurance. Learning shows motion without a predicted fill level.

| State | Stills | Behavior |
| --- | --- | --- |
| Ready to start | <img src="../assets/notifications/roadster/off-time/fill-000.png" width="58" height="58" alt="Roadster: Ready to start"> | Parked with an empty reserve and the wing stowed. |
| Epoch · learning | <img src="../assets/notifications/roadster/learning/active.png" width="58" height="58" alt="Roadster: Epoch · learning"> | Hovering on pulsing gas streams with the wing raised; no fill level or roll. |
| Epoch · countdown | <img src="../assets/notifications/roadster/active/fill-075.png" width="58" height="58" alt="Roadster: Epoch · countdown, 25% elapsed"> <img src="../assets/notifications/roadster/active/fill-050.png" width="58" height="58" alt="Roadster: Epoch · countdown, 50% elapsed"> <img src="../assets/notifications/roadster/active/fill-025.png" width="58" height="58" alt="Roadster: Epoch · countdown, 75% elapsed"> | Reserve drains as the car rises, rolls, and descends to land; one progress-driven roll from 45% to 55% elapsed, with lateral jets only within that interval. |
| Epoch · past expected end | <img src="../assets/notifications/roadster/overtime/active.png" width="58" height="58" alt="Roadster: Epoch · past expected end"> | Landed, empty reserve, wing stowed, and jets off. |
| Off-time · learning | <img src="../assets/notifications/roadster/learning/off-time.png" width="58" height="58" alt="Roadster: Off-time · learning"> | Parked with a pulsing recharge connection; no fill level. |
| Off-time · countdown | <img src="../assets/notifications/roadster/off-time/fill-025.png" width="58" height="58" alt="Roadster: Off-time · countdown, 25% elapsed"> <img src="../assets/notifications/roadster/off-time/fill-050.png" width="58" height="58" alt="Roadster: Off-time · countdown, 50% elapsed"> <img src="../assets/notifications/roadster/off-time/fill-075.png" width="58" height="58" alt="Roadster: Off-time · countdown, 75% elapsed"> | Parked with the reserve replenishing and the recharge connection visible. |
| Off-time · past expected start | <img src="../assets/notifications/roadster/overtime/off-time.png" width="58" height="58" alt="Roadster: Off-time · past expected start"> | Parked with a full reserve; recharge connection and jets off. |

## Updating the stills

The images are rendered from the production QML, rather than drawn separately. After changing a graphic, run `python3 scripts/notification_assets.py` from the repository root. See [development checks](development-checks.md) for rendering and centering requirements.
