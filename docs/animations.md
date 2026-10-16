# Animations

Choose a companion in **Settings → Animated graphic**. The choices appear in the order below, and each preview cycles through the same seven states.

These stills use the packaged notification assets. Countdown rows read left to right at **25%, 50%, and 75% of the predicted interval elapsed**. Other rows show one representative frame; the descriptions explain motion that a still cannot show. The live graphic uses your theme color and is dimmed during off-time.

“Learning” means there is no prediction yet. Passing an expected end or start keeps the current phase until you end or start the epoch yourself.

- [Sun and moon](#sun-and-moon)
- [Coffee cup](#coffee-cup)
- [Starship](#starship)

## Sun and moon

The sun represents an active epoch; the crescent moon represents off-time. Each descends toward the horizon as its predicted interval runs out. This follows your epochs, independently of actual daylight.

| State | Stills | Behavior |
| --- | --- | --- |
| Ready to start | <img src="../assets/notifications/sun-moon/off-time/fill-000.png" width="58" height="54" alt="Sun and moon: Ready to start"> | Sun peeking above the horizon, stationary. |
| Epoch · learning | <img src="../assets/notifications/sun-moon/learning/active.png" width="58" height="54" alt="Sun and moon: Epoch · learning"> | Sun at a fixed height with rotating rays; no predicted progress yet. |
| Epoch · countdown | <img src="../assets/notifications/sun-moon/active/fill-075.png" width="58" height="54" alt="Sun and moon: Epoch · countdown, 25% elapsed"> <img src="../assets/notifications/sun-moon/active/fill-050.png" width="58" height="54" alt="Sun and moon: Epoch · countdown, 50% elapsed"> <img src="../assets/notifications/sun-moon/active/fill-025.png" width="58" height="54" alt="Sun and moon: Epoch · countdown, 75% elapsed"> | Sun descends toward the horizon, with rotating rays. |
| Epoch · past expected end | <img src="../assets/notifications/sun-moon/overtime/active.png" width="58" height="54" alt="Sun and moon: Epoch · past expected end"> | Sun remains partly below the horizon; its rays gently pulse. |
| Off-time · learning | <img src="../assets/notifications/sun-moon/learning/off-time.png" width="58" height="54" alt="Sun and moon: Off-time · learning"> | Moon at a fixed height with twinkling stars; no predicted progress yet. |
| Off-time · countdown | <img src="../assets/notifications/sun-moon/off-time/fill-025.png" width="58" height="54" alt="Sun and moon: Off-time · countdown, 25% elapsed"> <img src="../assets/notifications/sun-moon/off-time/fill-050.png" width="58" height="54" alt="Sun and moon: Off-time · countdown, 50% elapsed"> <img src="../assets/notifications/sun-moon/off-time/fill-075.png" width="58" height="54" alt="Sun and moon: Off-time · countdown, 75% elapsed"> | Moon descends toward the horizon as the stars fade. |
| Off-time · past expected start | <img src="../assets/notifications/sun-moon/overtime/off-time.png" width="58" height="54" alt="Sun and moon: Off-time · past expected start"> | Moon remains at the horizon with a gentle pulse. |

## Coffee cup

The liquid level represents the remaining epoch or the progress of off-time. The cup empties during an epoch and refills during off-time.

| State | Stills | Behavior |
| --- | --- | --- |
| Ready to start | <img src="../assets/notifications/coffee/off-time/fill-000.png" width="58" height="54" alt="Coffee cup: Ready to start"> | Empty cup. |
| Epoch · learning | <img src="../assets/notifications/coffee/learning/active.png" width="58" height="54" alt="Coffee cup: Epoch · learning"> | Empty cup with drifting steam; no predicted fill level yet. |
| Epoch · countdown | <img src="../assets/notifications/coffee/active/fill-075.png" width="58" height="54" alt="Coffee cup: Epoch · countdown, 25% elapsed"> <img src="../assets/notifications/coffee/active/fill-050.png" width="58" height="54" alt="Coffee cup: Epoch · countdown, 50% elapsed"> <img src="../assets/notifications/coffee/active/fill-025.png" width="58" height="54" alt="Coffee cup: Epoch · countdown, 75% elapsed"> | Liquid level falls toward empty. |
| Epoch · past expected end | <img src="../assets/notifications/coffee/overtime/active.png" width="58" height="54" alt="Coffee cup: Epoch · past expected end"> | Cup stays empty. |
| Off-time · learning | <img src="../assets/notifications/coffee/learning/off-time.png" width="58" height="54" alt="Coffee cup: Off-time · learning"> | Empty cup with drifting steam; no predicted fill level yet. |
| Off-time · countdown | <img src="../assets/notifications/coffee/off-time/fill-025.png" width="58" height="54" alt="Coffee cup: Off-time · countdown, 25% elapsed"> <img src="../assets/notifications/coffee/off-time/fill-050.png" width="58" height="54" alt="Coffee cup: Off-time · countdown, 50% elapsed"> <img src="../assets/notifications/coffee/off-time/fill-075.png" width="58" height="54" alt="Coffee cup: Off-time · countdown, 75% elapsed"> | Liquid level rises toward full. |
| Off-time · past expected start | <img src="../assets/notifications/coffee/overtime/off-time.png" width="58" height="54" alt="Coffee cup: Off-time · past expected start"> | Cup stays full. |

## Starship

The fuel tank drains during an active epoch and refills on the launch pad during off-time.

| State | Stills | Behavior |
| --- | --- | --- |
| Ready to start | <img src="../assets/notifications/starship/off-time/fill-000.png" width="58" height="54" alt="Starship: Ready to start"> | Empty tank on the launch pad. |
| Epoch · learning | <img src="../assets/notifications/starship/learning/active.png" width="58" height="54" alt="Starship: Epoch · learning"> | Flickering nozzle flame, without a predicted fuel level. |
| Epoch · countdown | <img src="../assets/notifications/starship/active/fill-075.png" width="58" height="54" alt="Starship: Epoch · countdown, 25% elapsed"> <img src="../assets/notifications/starship/active/fill-050.png" width="58" height="54" alt="Starship: Epoch · countdown, 50% elapsed"> <img src="../assets/notifications/starship/active/fill-025.png" width="58" height="54" alt="Starship: Epoch · countdown, 75% elapsed"> | Fuel drains while the nozzle flame flickers. |
| Epoch · past expected end | <img src="../assets/notifications/starship/overtime/active.png" width="58" height="54" alt="Starship: Epoch · past expected end"> | Empty tank with the flame off. |
| Off-time · learning | <img src="../assets/notifications/starship/learning/off-time.png" width="58" height="54" alt="Starship: Off-time · learning"> | Pulsing fuel connection on the launch pad, without a predicted fuel level. |
| Off-time · countdown | <img src="../assets/notifications/starship/off-time/fill-025.png" width="58" height="54" alt="Starship: Off-time · countdown, 25% elapsed"> <img src="../assets/notifications/starship/off-time/fill-050.png" width="58" height="54" alt="Starship: Off-time · countdown, 50% elapsed"> <img src="../assets/notifications/starship/off-time/fill-075.png" width="58" height="54" alt="Starship: Off-time · countdown, 75% elapsed"> | Fuel fills on the launch pad. |
| Off-time · past expected start | <img src="../assets/notifications/starship/overtime/off-time.png" width="58" height="54" alt="Starship: Off-time · past expected start"> | Full tank on the launch pad. |

## Updating the stills

The images are rendered from the production QML, rather than drawn separately. After changing a graphic, run `python3 scripts/notification_assets.py` from the repository root. See [development checks](development-checks.md) for rendering and centering requirements.
