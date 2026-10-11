# Plan: live anatomy library, checked against video

Date: 2026-10-11

## Goal

Generate a core anatomy library, then a few lifts, with no studio animation. Play them live on our own model. Check each claim against a reference. Do not copy Muscle & Motion frames, meshes, or text.

The four M&M apps (Anatomy, Strength, Yoga, Posture) are one body plus four indexes. We are not cloning their catalog. Background is in `docs/apps-and-live-generation.md`. The exam diagram is in `docs/show-me-verification.html`.

## Constraints

- No hand-keyed animation and no stored video library. A library entry is a model plus a motion spec, rendered on open.
- Default motion source: track a reference video, project it onto our skeleton, replay it on our model. The video is inspiration and a test, not texture.
- Joint models reject illegal motion. They do not pick the squat in the video. The video picks which legal motion this person did.
- Muscle colors are model estimates, not EMG.
- Do not train on M&M clips. Do not rip their media.

## What stays open

The exam is fixed. The stack is not. These slots can all have more than one prototype:

- Skeleton: OpenSim paths, SKEL, or another constrained model
- Tracker: WHAM, HMR, OpenCap monocular, or another
- Muscle estimator: moment-arm sign, static optimization, or a learned prior
- Motion source: video retarget (default), a Moco task solve, or a scripted isolate
- Drawing: lines, fusiform meshes, or volume

Each prototype emits the same record:

```text
joint_angles(t)
muscle_roles(t)
load assumption
confidence
```

The harness scores that record. It does not call the prototype's tracker or the prototype's muscle solver.

## How we verify

A prototype must not grade itself. If playback is the track replayed, scoring it against that same track always passes. That test is banned. The driving track and the scoring track must differ.

Each score is pass, fail, or abstain.

| Score | Held-out evidence | Starting gate |
|---|---|---|
| Legality | The skeleton's own limits and couplers | No frame outside a hard limit. Abstain if this model has no limit for that joint. |
| Joint path | A second tracker, or a few hand-labeled frames | Mean error under 10° on visible major joints, none over 20°. Abstain if under 70% of those joints are visible, or the clip is a mirror or cropped. |
| Muscle role | A label set written before the run | Top-5 overlap at least 0.6, and no prime mover with the wrong moment-arm sign. Abstain if the load direction is unknown. |
| Negative control | A different exercise under the same name | Must fail muscle-role. Abstain if the decoy clip is too messy to trust. |

The degree and overlap numbers rank prototypes. They are not clinical truth. Tune them after two prototypes exist.

Muscle-role agreement means set overlap, not pixel overlap. A prime mover pulls with the task. A synergist helps that pull. A stabilizer holds a joint the task would otherwise move. An antagonist opposes it. For a face pull the frozen set is rear deltoid, infraspinatus, teres minor, middle trapezius, lower trapezius, and rhomboids. Painting latissimus as the prime mover fails even if the arms look right.

## First exam

1. Anatomy isolates. Biceps flexion, triceps extension, glute max hip extension. No video. Moment-arm sign must match the action table.
2. Squat, person in frame. Joint path plus vasti and glute max roles. Assume a vertical load over the midfoot.
3. Face pull, person in frame. Muscle-role score leads. The scapula will not track well, so that path may abstain. Load is a cable pulling forward from the hands.
4. Rotator-cuff force couple. Teaching claim, not a pose match. Subscapularis must oppose infraspinatus and teres minor. Sample clip: https://www.youtube.com/watch?v=sRNakktrOGE
5. Negative control. A lat pulldown or row labeled "face pull" must fail muscle-role.

A prototype can pass the squat and fail the face pull. Keep it. The card is there to compare stacks, not to kill all but one.

## Exploration order

1. Write the harness and the frozen label sets before betting on a body model.
2. Anatomy viewer: click a muscle, play the joint action its moment arm can produce.
3. Run two trackers on one squat file and one face-pull file. One drives playback. The other scores.
4. Run two muscle painters on the same retarget: moment-arm sign, and static optimization with the assumed load.
5. Optional third motion source: a Moco squat with feet planted and a depth target. Score it on the same held-out track so we can see what the model does without the video.

Do not expand to yoga, posture, or a large exercise list until the squat and face pull reports are honest, including abstains.

## Out of scope

- Cloning 1,200 exercises
- Matching M&M lighting, mesh, or brand
- Claiming measured muscle activation from one RGB video
- Clinical or injury-risk advice
