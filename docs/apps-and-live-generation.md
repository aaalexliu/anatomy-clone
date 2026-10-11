# All Muscle & Motion apps, and a live-generation path

Date: 2026-10-11
Constraint from product intent: no hand-crafted studio animation. The core library and the playback must be generated live. A reference video (YouTube or otherwise) is a check, not a source to copy frames from.

## The four apps are one corpus with four indexes

M&M sells four subscriptions, not four engines. Anatomy content is reused inside Strength, Yoga, and Posture. Do not add the video counts.

| App | What the user browses | Published size | What is actually distinct |
|---|---|---|---|
| Anatomy | Muscles, origins, insertions, actions, kinesiology clips, 3D model (muscle / bone / joint layers) | 2,000+ 3D muscle videos | The atlas. Every other app hangs off this. |
| Strength | Exercises, mistakes, cues, plans, client assignment | 1,200+ exercises, plus theory clips | Exercise index + mistake variants + planner. |
| Yoga | Asanas, errors, prep drills | 80+ poses, 100+ therapeutic clips claimed on some pages | Pose index. Same body, different joint targets and stretch emphasis. |
| Posture | Disorders (kyphosis, lordosis, flat back) and corrective drills | Count not published | Disorder index + therapeutic exercise index. |

Courses (one-time, not apps): Functional Training Anatomy, Anatomy and Biomechanics of Movement, and similar. They are packaged teaching on top of the same visuals. Not a fifth engine.

Shared product atoms:

1. A body you can see through.
2. A motion (isolated muscle action, lift, pose, or corrective drill).
3. A muscle-role overlay (agonist, synergist, stabilizer, antagonist, or a force couple).
4. A short teaching claim (what is moving, what is wrong, what to do instead).
5. Links: muscle -> motions, motion -> muscles, disorder -> drills.

Their production page still describes animator + multi-month review. That is their process. It is not a requirement of the category if we accept a model-generated body.

Package ids (legacy AIR naming, not proof of current runtime):

- `air.com.musclemotion.anatomy`
- `air.com.musclemotion.strength.mobile`
- `air.com.musclemotion.yoga`
- `air.com.musclemotion.posture`

Web apps: `app.anatomy.muscleandmotion.com`, strength/yoga/posture equivalents.

## What the sample video actually is

https://www.youtube.com/watch?v=sRNakktrOGE

- Title: **The Rotator Cuff Force Couples**
- Channel: **Muscle & Motion**

This is a teaching clip about shoulder force couples, not a person performing a named gym set. Two different checks get confused if we treat every URL as the same kind of ground truth:

| Reference type | Example | What "correct" can mean | What it cannot mean |
|---|---|---|---|
| Person moving | gym form video | Joint path close to the person in frame | Which muscle "should" fire. Pose does not uniquely decide EMG. |
| Teaching animation | this rotator-cuff clip | Same muscles named, same line-of-action story, same resultant force direction | Pixel match to their mesh, lighting, or camera. |

## What "generated live, no studio" forces

Do not store a video library. Store a **model** and **motion specs**. Render on open.

### Layer 1 - body (one asset, all four apps)

Need a skeleton with realistic joint limits plus muscle paths (origin, insertion, via points), not a cosmetic SMPL skin alone.

Practical pieces, all with license checks before product use:

- **SMPL / SMPL-X**: visual body and pose from video. No muscles.
- **SKEL**: skeleton + skin, biomechanical joint limits, fits SMPL sequences. Still not a muscle atlas.
- **OSSO**: bones inside a skin. Useful for the bone layer.
- **OpenSim models** (gait2392, Rajagopal, upper-extremity models): muscle paths and moment arms. This is the atlas.
- **OpenCap**: video -> 3D kinematics -> muscle-driven dynamics. Closest existing pipeline. Multi-phone is validated; monocular is newer and cloud/post-hoc, not a proven on-device live muscle readout.

A live viewer is three.js (or similar) drawing:

- bone meshes or simplified bones
- muscle polylines or simple fusiform meshes along OpenSim paths
- color by estimated activation or by role
- camera orbit independent of the motion

That covers the Anatomy app's "origin, insertion, action" if each muscle clip is a **script**: set pose, highlight one muscle, play its joint action. No animator.

### Layer 2 - motion (the library)

A library entry is data, not a file from an artist:

```
id, name, app_tags[]
joint_targets over time   # or a tracked reference trajectory
contact / equipment constraints
external load assumption   # bodyweight, bar path, band
role_overrides optional    # only when the model is known-wrong
teaching_claims[]          # text we are willing to defend
```

Two legal sources of motion, both non-studio:

1. **Procedural.** Script joint angles (squat: hip/knee/ankle coupled; shoulder abduction: glenohumeral + scapular rhythm). Best for Anatomy isolated actions, basic posture drills, basic yoga shapes.
2. **Tracked from a reference video.** Run pose estimation, retarget onto our skeleton, store the trajectory, replay it live on our muscle body. The video is a motion donor or a test, not a texture to copy.

"Live" here means **render and recompute on demand**. It does not mean invent a bench-press trajectory with no physical prior. A prior can be a formula, a tracked video, or a biomechanics paper. It cannot be a hand-keyed Maya scene.

### Layer 3 - muscle state

Color is the product. Pose alone is not enough.

Same elbow angle can be biceps, brachialis, or a co-contraction. M&M's colors are expert labels. A generator must say which estimator it used:

- **Line-of-action / moment-arm sign.** Fast, live, good enough to show "this muscle can produce this joint moment." Weak on stabilizers and co-contraction. Good first pass for Anatomy and for force-couple diagrams (rotator cuff).
- **Static optimization (OpenSim).** Needs external forces. Fine for supported lifts and gait-like tasks if we assume a load. Too slow and too assumption-heavy for true 60 fps on every muscle, but fast enough to precompute a curve and play it live.
- **Learned activation (Muscles in Action, BioHuman).** Small muscle sets, exercise sets, or sim labels. Useful as a prior, not as clinical truth.

Honest label on screen: **model estimate**, not "measured activation."

### Layer 4 - verification against any video

Pipeline:

1. Identify the reference class (person moving vs teaching diagram vs mixed).
2. If a person is in frame: track 3D pose (WHAM, HMR2.0, or OpenCap monocular). Map to our skeleton. Score joint-angle error over time, plus foot/contact failures.
3. Run our muscle estimator on **our** retargeted motion and, separately, on the **reference** pose track.
4. Score agreement: top muscles, timing of peaks, left/right, and (for force-couple clips) resultant vector direction.
5. Fail closed when the track is bad: bar occlusion, mirror, cropped limbs, fast camera move. Show "cannot verify," do not invent a pass.

What a pass is **not**:

- Looking like the M&M thumbnail.
- Matching their exact color palette.
- Claiming EMG accuracy from one RGB video.

Known hard cases: barbell occlusion, gym mirrors, baggy clothes, cable machines, scapula (barely visible), deep stabilizers (transversus, rotator cuff). The sample video is in that last bucket. Pose match will not prove the force couple. Muscle-line direction and which muscles are tagged will.

## How each app falls out of one generator

| App | Live generator | Verification |
|---|---|---|
| Anatomy | Muscle table from OpenSim paths. Isolated action = joint script + highlight. 3D model = same viewer, layers toggled. | Check attachment names and action against a textbook table, not against their video pixels. Use their public clip only as a claim to test ("does our model show this force couple?"). |
| Strength | Exercise = trajectory + load assumption + equipment constraint. Mistakes = the same spec with one joint offset (knees in, lumbar flexion). | Person-in-frame videos: joint score. Teaching clips: muscle-role score. |
| Yoga | Pose = hold trajectory + stretch side (muscle length) vs strength side (activation). | Joint angles of the shape, plus lengthened-muscle set. |
| Posture | Disorder = resting joint offsets from neutral. Drill = trajectory that reduces those offsets. | Resting-pose estimate vs described disorder, then drill direction. |

One schema, four queries. That is the core library.

## What is feasible now vs not

Feasible for a first live core:

- Shared viewer: skeleton + muscle lines, orbit, isolate, play.
- Anatomy library generated from a musculoskeletal model (hundreds of muscles, scripted actions).
- A small strength/yoga/posture set whose motions are either scripted or tracked from a reference video you supply.
- Verification report: joint error, contact failures, top-muscle overlap, and a clear abstain.

Not feasible if the bar is "indistinguishable from M&M, clinically true, on any YouTube URL, at 60 fps, with no disclaimers":

- Monocular muscle force is underdetermined.
- Upper-limb and scapula models are weaker than gait models.
- OpenCap-class dynamics are not a casual live web call yet.
- Their translucent skinned look is an art direction on top of the model. We can approximate volume. We should not chase their frames.

## Shared constraints, open prototypes (2026-10-11)

These are constraints. They are not one pipeline.

1. Two scores, and either may abstain. Joint-path error against a held-out track of the person. Muscle-role overlap against a frozen label set. Do not grade a prototype against the same tracker or the same muscle estimator that produced it.
2. Default motion source: track a reference video, project it onto our skeleton, replay it on our model. The video is inspiration and a test, not texture to copy. Other motion sources (a Moco task solve, a hand-scripted isolated action) may sit in the same exam.
3. First exam items: Anatomy isolates, one squat, one face pull, plus the rotator-cuff force-couple claim. More items can be added without changing the harness.

Prototype slots that stay open: which skeleton, which tracker, which muscle estimator, which renderer. They all emit the same report. The exam picks a winner. It does not freeze the stack on day one.

See `docs/show-me-verification.html` for the harness.

Joint limits do not emit the path. See the note below.

## Why a joint model does not emit "the" path

A biomechanical model is a feasible set plus some couplings. It is not a function from exercise name to trajectory.

What good models actually constrain:

- **Rajagopal 2016 (OpenSim).** Knee flexion is the free coordinate. Tibial rotation, ab/adduction, and translations are prescribed functions of flexion. That removes redundancy *inside the knee*. It does not decide how deep the squat is, how much the hips flex, or how far the torso leans.
- **MoBL-ARMS (OpenSim upper limb).** Scapular motion is a regression on humeral elevation (a scapular rhythm), not a free measured scapula. Papers warn that this prescribed rhythm misses natural and injured scapular motion. Face pull is mostly retraction and external rotation, which that rhythm was not built to invent.
- **SKEL.** Better joint centers and min/max limits than SMPL. A limit is a box. Many paths sit inside the box.
- **AnyBody.** Strong joint constraints and muscle recruitment, but the usual solve assumes the motion is already prescribed. Constraints then distribute force. They do not choose the motion.
- **OpenSim Moco.** This is the solver that can grow a trajectory from task constraints and a cost (feet planted, hands on a target, minimum effort) with no mocap. The result is one optimal path under that cost, not the unique human path. Change the cost or the stance width and you get another legal squat.

So:

- Impossible motion is rejected by the model (hyperextension, knee secondary motion that breaks the coupling, bone intersection).
- The particular squat in a video does not fall out of the knee model. The video answers which member of the family this person performed.
- Pipeline: track video -> project onto legal coordinates (drop or recouple DOFs the model forbids) -> replay on our skeleton -> solve muscle forces for that motion and an assumed load.

Muscle forces are a second redundancy. Once the path and the external load are fixed, many muscle combinations can still produce the same joint moments (co-contraction). Recruitment optimization picks one. That pick is a model estimate.

## What muscle-role agreement means

M&M does not only move a skeleton. It paints muscles by job:

- prime mover: pulls in the direction of the task
- synergist: helps that same moment
- stabilizer: holds a joint that the task would otherwise move
- antagonist: opposes the task moment, or lengthens under load

Agreement is set overlap, not pixel overlap. Example for a face pull: reference set is rear deltoid, infraspinatus, teres minor, lower and middle trapezius, rhomboids. Our estimator, given the retargeted motion and a backward cable load, must rank those as the muscles producing the horizontal abduction and external-rotation moments. Score = overlap of the top muscles, plus a miss if we highlight a muscle whose moment arm has the wrong sign (a lat-dominant row, for example).

The rotator-cuff clip is this kind of test. Pose match is the wrong score. The score is whether our lines of action form the same couple: subscapularis versus infraspinatus and teres minor, and deltoid versus supraspinatus for elevation.

## How verification runs

The stable object is the exam, not the prototype. Each prototype emits `joint_angles(t)`, `muscle_roles(t)`, a load assumption, and its own confidence. A separate harness scores that emission. The harness never calls the prototype's tracker or the prototype's muscle solver.

Scores:

| Score | Evidence, held out | Pass, as a starting gate | Abstain |
|---|---|---|---|
| Legality | The skeleton's own limits and couplers | No frame outside a hard limit | Model has no limit for that joint |
| Joint path | A second tracker, or a few hand-labeled frames | Mean abs error under 10° on visible major joints, no joint over 20° | Under 70% of major joints visible, mirror, cropped limbs |
| Muscle role | A label set written before the run (textbook, EMG note, or the claim in a teaching clip) | Top-5 overlap at least 0.6, and no prime mover with the wrong moment-arm sign | Load direction unknown |
| Negative control | A clip of a different exercise under the same name | Must fail muscle-role | Clip is too ambiguous to be a control |

Those degree and overlap numbers are comparison gates, not clinical truth. Tune them once two prototypes exist. Do not treat a self-match as a pass.

First exam card:

1. Anatomy isolate. Biceps flexion, triceps extension, glute max hip extension. No video. Moment-arm sign must match the action table.
2. Squat, person in frame. Joint path plus vasti / glute max roles. A lat-pulldown labeled "squat" must fail.
3. Face pull, person in frame. Muscle-role score leads. Scapula path may abstain.
4. Rotator-cuff force couple, teaching clip. Lines of action must oppose: subscapularis versus infraspinatus and teres minor. Pose match is not the score.

## Exploration order

Build the exam harness before betting on a stack. Then run more than one prototype through it.

- Body: muscle lines on OpenSim paths, versus SKEL joints with a thinner muscle set.
- Tracker: two monocular trackers on the same squat and face-pull files. The one not used to drive playback is the held-out score.
- Muscles: moment-arm sign, versus static optimization with an assumed load. Same frozen labels.
- Motion source check: video retarget versus a Moco squat. Both get the same joint-path score against the held-out track. This shows what the model would have done without the video, without making that the only path.

Do not start by cloning 1,200 exercises or by training on M&M frames.

## Sources

- https://www.muscleandmotion.com/products-apps-courses/
- https://www.muscleandmotion.com/muscular-anatomy-app/
- https://www.muscleandmotion.com/strength-training-app/
- https://www.muscleandmotion.com/yoga-functional-anatomy-app/
- https://www.muscleandmotion.com/posture/
- https://www.muscleandmotion.com/quality-commitment/
- https://www.youtube.com/watch?v=sRNakktrOGE (Muscle & Motion, "The Rotator Cuff Force Couples")
- SKEL: https://skel.is.tue.mpg.de/
- OpenCap: https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1011462
- OpenCap Monocular: https://arxiv.org/abs/2603.24733
- Muscles in Action: https://musclesinaction.cs.columbia.edu/
- SMPL-X: https://smpl-x.is.tue.mpg.de/
