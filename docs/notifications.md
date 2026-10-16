# Notifications

Plancks sends local desktop notifications for optional epoch inspiration and insights, expected-finish warnings, manual previews, and session stage targets. This is the reference for their variations, wording, timing, and image format.

## Card format

Every variation uses the same delivery format:

| Field | Format |
| --- | --- |
| App and title | `Plancks` |
| Body | One concise message; examples below use actual templates with illustrative values. |
| Icon | A still of the selected animation at the current epoch/off-time state. |
| Urgency and sound | Normal urgency, silent. |
| Timeout | Requests 8 seconds; the desktop controls final presentation. |
| Actions | No notification action buttons; session transitions happen in the panel. |

Custom session names are displayed literally: markup characters are escaped before delivery.

## Variations and examples

| Variation | Control or trigger | Example body |
| --- | --- | --- |
| Attributed quote | Occasional insights | A short science or technology quote followed by its author; sources below. |
| Reflective prompt | Occasional insights | `Try the smallest experiment that could change your mind.` |
| Elapsed-time reflection | Occasional insights, eligible after 3 hours | `4 hours into this epoch. What has become clearer?` |
| Historical observation | Occasional insights, when an eligible fact exists | `25 included epochs completed.` |
| Expected-finish warning | Finish notifications, at a configured threshold | `30 minutes to your expected finish. Choose what you want to leave complete.` |
| One-minute warning | Finish notifications, when the threshold is exactly 1 minute | `One minute to your expected finish. Leave a note for where to pick up.` |
| First extra-time check-in | Occasional insights, once about 90 seconds past the prediction | `Past the estimate. A useful moment to decide whether to continue or wrap up.` |
| Later extra-time reflection | Occasional insights, eligible at least 1 hour past the prediction | `An extra 1 hour. Keep the time intentional.` |
| Manual preview | Preview in Settings | Uses the quote/prompt/observation selection, with no preview prefix. |
| Activity target | Session activity reaches its target | `Activity time reached · Start rest when ready` |
| Rest target | Session rest reaches its target | `Rest time reached · Start activity when ready` |
| Long-rest target | Session long rest reaches its target | `Long rest time reached · Start activity when ready` |
| Final stage target | Last session stage reaches its target | `Rest time reached · Finish session when ready` |

Session messages follow `[name · ]{Activity|Rest|Long rest} time reached · {next action} when ready`. The name prefix is omitted for unnamed sessions. The final stage always uses `Finish session`, regardless of stage type. For example: `Study · Activity time reached · Start rest when ready`.

Durations in insight messages use readable units such as `30 minutes` or `1 hour 30 minutes`, rather than the panel’s signed clock format. The examples are representative; wording rotates within each category.

## Settings and scheduling

The **Notifications** section in Settings groups **Occasional insights**, its frequency and Preview controls, **Motivational quotes**, and **Finish notifications**.

**Motivational quotes** is enabled by default and can be switched off independently. It controls attributed quotes in both scheduled occasional insights and Preview. Historical observations and original reflective prompts remain available, and finish/session alerts are unaffected. Changing this preference does not enable notifications.

Settings has two independent, optional notification controls. Both start off. **Occasional insights** offers attributed quotes, reflective prompts, historical observations, and one extra-time check-in. **Finish notifications** defaults to 30 minutes and 1 minute before the expected end; edit the comma-separated minute values to choose up to six thresholds. Alerts appear as normal desktop notifications while an epoch is active. Off-time is quiet. **Preview**, beside the frequency choices, sends a sample note through the same desktop notification path as scheduled alerts. It works even with notifications disabled or during off-time, without changing history or delivery progress. Repeated previews remember recent samples for the current shell session, varying the observation and wording independently of scheduled alerts.

The first occasional note is scheduled 90–105 minutes into an epoch. Subsequent spacing varies randomly: **Light** every 3–4 hours, **Standard** every 2–3 hours, or **Frequent** every 1–2 hours. Passing the prediction produces one extra-time check-in after about 90 seconds, and occasional notes continue. Finish warnings take priority over occasional notes; closely spaced alerts are separated by a two-minute cooldown. Missed alerts after suspend or restart are skipped rather than delivered in a burst. Enabling notifications midway through an epoch does not send past warnings.

During a session’s activity stage, scheduled occasional notes are suppressed. Expected-finish warnings and the first extra-time check-in remain eligible. Session target alerts are independent of both optional notification switches: each stage sends one at its target. They do not advance the stage automatically.

A missed session target is delivered once when possible after recovery. This differs from missed epoch insight/finish alerts, which are skipped. Pausing freezes stage progress until resumed.

## Observation and wording variation

The local catalog varies both wording and meaning, remembering recent messages and the historical facts already shown. Eligible observations include completed-epoch milestones, improving start-time consistency, steady epoch lengths, monthly opportunity totals, earlier starts, morning patterns, monthly duration records, and forecast accuracy. Statistics use valid, included history; monthly totals count completed epochs that started in the current local calendar month. Time recorded describes opportunity, not work accomplished. Forecast accuracy compares the prediction saved at completion with the actual finish, using predictions saved with newly completed epochs; older entries without that information are omitted.

When eligible historical observations exist, selection chooses one with a 65% chance. Otherwise, it chooses a fresh quote with a 65% chance when one is available, or an original reflective prompt. Quotes already in the last 30 messages are ineligible; the last four categories are also avoided. When all quotes are recent, prompts provide variety until a quote ages out of that window. Recent categories, exact messages, and previously shown facts are tracked separately. Preview has its own session-local selection history, so it does not consume scheduled observations.


### Additional historical observations

| Observation | Eligibility and calculation |
| --- | --- |
| Typical epoch length | Median duration of the last five valid, included completed epochs. |
| Typical off-time | Median duration of the last five valid, included off-time intervals. This describes recorded off-time, not sleep. |
| Weekly summary | At least three completed, included epochs starting in the anchor’s local ISO week; reports their count and combined duration. In-progress time is excluded. |
| Improving forecast error | Ten eligible completed epochs with saved predictions. Compares median absolute error for the latest five against the previous five; shown when the old error is at least one minute and the new error is at least 25% smaller. |

These observations share the existing history cache and fact deduplication. Weekly and monthly grouping uses the current epoch/start anchor’s local calendar, matching the other historical insights. Longer time is not described as better work.

## Quote sources and editorial approach

Selections focus on curiosity, invention, exploration, and learning; political advocacy, personal attacks, and culture-war commentary are excluded. Quotes are short, attributed excerpts, stored locally with their source URL. They are not paraphrased into the author's voice or combined with generated praise. Original prompts are unquoted and unattributed. Historical notes describe the measured pattern without claiming that elapsed time proves productivity or achievement. Finish warnings remain clear about time; extra-time notes invite a deliberate choice rather than automatically praising a longer day.

| Author | Excerpt used | Verification source |
| --- | --- | --- |
| Steve Jobs | Your time is limited, so don’t waste it living someone else’s life. | [Source](https://news.stanford.edu/stories/2005/06/steve-jobs-2005-graduates-stay-hungry-stay-foolish) |
| Richard Feynman | What I cannot create, I do not understand. | [Source](https://magazine.caltech.edu/post/biology-through-the-eyes-of-a-physicist) |
| Katherine Johnson | There's always something else that hasn't been found yet, so help them find it. | [Source](https://time.com/4779086/katherine-goble-johnson-nasa-hidden-figures/) |
| Alan Kay | The best way to predict the future is to invent it. | [Source](https://computerhistory.org/wp-content/uploads/2019/08/core-2012.pdf) |
| Grace Hopper | I think I always looked for the easiest and best, most accurate way of getting something done. | [Source](https://archive.computerhistory.org/resources/text/Oral_History/Hopper_Grace/102702026.05.01.pdf) |
| Alan Turing | We can only see a short distance ahead, but we can see plenty there that needs to be done. | [Source](https://turingtrust.co.uk/about-us/alan-turing/) |
| Albert Einstein | The important thing is not to stop questioning. | [Source](https://www.pbs.org/wgbh/nova/einstein/wisd-nf.html) |
| Elon Musk | I think Apollo 11 was one of the most inspiring things in all of human history. | [Source](https://time.com/5628572/elon-musk-moon-landing/) |
| Peter Thiel with Blake Masters | But every time we create something new, we go from 0 to 1. | [Source](https://penguinrandomhousehighereducation.com/book/?isbn=9780804139304) |
| John F. Kennedy | We choose to go to the moon in this decade and do the other things, not because they are easy, but because they are hard. | [Source](https://www.jfklibrary.org/learn/about-jfk/historic-speeches/address-at-rice-university-on-the-nations-space-effort) |
| Sally Ride | Science is fun. Science is curiosity. We all have natural curiosity. | [Source](https://assets.science.nasa.gov/content/dam/science/cds/researchers/nac/apac/2017/Harman_GS_Stars_APAC_July_2017_Tagged.pdf) |
| Frances Arnold | And the way to be innovative or the way to find what you love to do is to try different things. | [Source](https://thereader.mitpress.mit.edu/in-conversation-with-nobel-laureate-frances-arnold/) |

Sources include a commencement transcript, an oral history, institutional archives, and a sourced quotation collection. Preserve the source and exact excerpt when extending the catalog; omit uncertain attributions. No network access is needed when showing a quote.

## Animation snapshots

The icon follows the selected Sun and moon, Coffee cup, Starship, or Roadster graphic. It represents the epoch/off-time state, including for session target alerts; it does not represent the session stage timer. See [Animations](animations.md) for the illustrated state reference.

Predicted fill is rounded to the nearest 5%. Learning and overtime use dedicated stills. Each PNG has a white foreground with the drawing’s intentional transparency and a transparent background. The exporter trims unused canvas margins, fits the complete silhouette proportionally within 108 × 108 pixels, and centers it on a 116 × 116 canvas. This leaves a small border while making use of Omarchy’s 40 × 40 notification icon slot. Tall or wide shapes retain their proportions.

The snapshot is captured from the current state when the alert is queued. It is static, so moving exhaust and other motion appear at a representative frame. Snapshot fitting is separate from the fixed live animation canvas.

## Delivery and recovery

Scheduling runs in the existing Python helper. Ordinary ticks check an in-memory deadline; historical aggregates rebuild only when history changes. Delivery progress is saved atomically at scheduling or notification events, preventing duplicate delivery across restarts and helper instances. A short-lived Python helper receives each alert through stdin and delivers it over D-Bus using Omarchy’s Python GObject dependency. Custom session names and notification contents never enter process arguments; there is no additional resident process or network dependency. Insight errors appear in Settings without stopping the clock.

Session target milestones are durably claimed in the session journal before delivery. A crash between claiming and desktop delivery can lose an alert, but cannot repeat it or change the running stage. Epoch alert claims similarly prevent duplicates across restarts.

## Maintaining the assets

Install ImageMagick, then run `python3 scripts/notification_assets.py` from the repository root after graphic changes. The generator renders production QML, applies the white foreground, and automatically trims and fits every still. Assets live in `assets/notifications/{sun-moon,coffee,starship,roadster}/`, with `active`, `off-time`, `learning`, and `overtime` folders.

Run `python3 -m unittest discover -s tests -p test_notification_assets.py` to check packaged state coverage, square dimensions, and RGBA format. See [Development checks](development-checks.md) for the wider rendering and validation workflow.

Implementation references: [message catalog and scheduler](../insights.py), [session target emission](../plancks.py), [snapshot selection](../Graphics.js), [delivery queue](../EpochController.qml), [D-Bus delivery](../notification_send.py), and [asset generator](../scripts/notification_assets.py).
