# Muscle & Motion Strength - research brief (seed)

Date: 2026-10-11
Target product: Muscle & Motion Strength Training app
Goal of this repo: understand the core technological building blocks (especially the 3D exercise videos / anatomy motion) and evaluate whether / how a similar system can be regenerated legally from first principles.

## What the product is

Muscle & Motion Strength is not primarily a workout logger. It is a visual education product:

- 1,200+ strength exercises
- translucent 3D body animations that show muscle action under the skin
- biomechanics labels: prime movers, synergists, stabilizers, antagonists
- joint actions / planes of motion
- common-mistake overlays
- interactive 3D anatomical model (muscles / bones / joints), linked to exercises
- trainer features: build plans, assign to clients

Surfaces: iOS, Android, web. Subscription content library.

Primary public pages:

- https://www.muscleandmotion.com/strength-training-app/
- https://apps.apple.com/us/app/muscle-motion-strength/id1302056349
- https://play.google.com/store/apps/details?id=air.com.musclemotion.strength.mobile
- https://www.muscleandmotion.com/knowledge-center/how-we-analyze-exercises/
- https://www.muscleandmotion.com/knowledge-center/the-3d-model/
- https://www.muscleandmotion.com/quality-commitment/
- https://www.muscleandmotion.com/knowledge-center/system-requirements/

## Early technical read (unverified in depth)

### Content layer (the hard part)

Public materials strongly suggest the distinctive asset is **hand-authored 3D anatomical animation content**, not live motion capture shown to users and not a public 3D asset export.

Their stated production pipeline for each new exercise/video:

1. Idea selection (often subscriber requests)
2. Conceptualization by PTs / trainers / movement pros
3. Professional review
4. Text + coaching guide creation
5. Animation production by animators
6. QA
7. Translation
8. Publish

They claim some pieces take **3+ months** because of review loops.

Educational methodology claims:

- translucent 3D figure so musculoskeletal system is visible
- joint actions by plane
- mechanical anchors (fixed vs mobile attachments)
- origins / insertions / innervation overlays
- common-mistake skeleton+muscle overlays
- exercise <-> muscle database linkage

Implication: the moat is less "an app shell" and more **a large, expert-reviewed animation + taxonomy corpus**.

### Delivery / app layer (the easier part)

A vendor case study (Emyoli) describes M&M as a **Netflix-like streaming platform** for a large library of 3D anatomy videos, after starting as door-to-door CD sales of Flash-era content.

Claimed platform stack in that case study (may be partial / dated):

- Backend: PHP (CodeIgniter), MongoDB, Postgres
- Frontend web: React + Material UI
- Mobile: React Native (also icons for Swift/Kotlin shown)
- Infra: AWS, Docker, Lambda, Jenkins, CDN for video throughput
- Payments: Stripe
- Migration narrative: Flash video library -> modern web/mobile streaming

Android package id still uses Adobe AIR-style naming:

- `air.com.musclemotion.strength.mobile`
- Anatomy app historically: `air.com.musclemotion.anatomy`

That is a strong hint of **legacy AIR packaging / branding**, not proof the current runtime is still AIR.

System requirements page emphasizes **HD 3D animations and video streaming**, offline cache on mobile, and a fast connection on desktop. That fits **pre-rendered or server-delivered video** plus a separate interactive 3D model, more than a fully offline game-engine library of every exercise.

### What is unknown (must research)

- Are exercise demos pre-rendered video (mp4/hls), real-time 3D (Unity/Unreal/three.js), or hybrid (video + separate interactive model)?
- What DCC tools produce the animations (Maya, Blender, Cinema4D, 3ds Max, custom)?
- Do they use a shared base body rig + muscle deformation system, or bespoke clips per exercise?
- Is muscle activation driven by:
  - hand keyframes
  - physics / muscle simulation
  - motion capture retargeted onto anatomy
  - procedural biomechanics rules
- Codec / streaming protocol / CDN path on web
- Schema of exercise metadata (muscles, equipment, plane, mistakes, cues)
- How the interactive 3D model is shipped (glTF, proprietary viewer, engine embed)
- Whether any licensing / white-label / institutional API exists
- Exact current mobile stack vs legacy AIR package ids

## Legal / ethics boundary for this project

Allowed:

- study public product behavior, marketing, patents, papers, job posts, store listings
- inspect **your own** licensed session traffic / client behavior at a high level for architecture understanding
- design an original regeneration pipeline and original assets
- compare open datasets, open anatomy models, commercial anatomy engines, mocap pipelines

Not allowed:

- ripping M&M video files, models, textures, or metadata dumps for redistribution
- training a generator on their proprietary clips to clone look-and-feel
- circumventing DRM / paywall / offline-store protections
- shipping a confusingly similar brand or copied exercise analysis text

"Clone the product category" is fine. "Copy their corpus" is not.

## Competing / adjacent building blocks to investigate

Product comps:

- Complete Anatomy / 3D4Medical (interactive medical 3D, muscle movement)
- AnatoFit (gym exercises on anatomical 3D model)
- Visible Body
- Physiotherapy / PT education animation libraries
- generic exercise demo apps with 2D GIFs (much weaker)

Open / semi-open pieces:

- anatomy meshes / body models (BodyParts3D, various commercial rigs)
- muscle-group SVG / highlight libraries (e.g. anatome-style maps)
- free exercise databases with GIFs/metadata (quality far below M&M)
- pose estimation (MediaPipe, OpenPose, commercial mocap) as input to a custom visualizer
- Blender / Unity / Unreal / three.js + React Three Fiber for viewers
- biomechanics engines / OpenSim-like simulation (heavier, research-grade)

## Working hypothesis to confirm or kill

M&M Strength ≈

1. **Content studio system**: shared anatomical human + rig + look, expert exercise brief, animator produces clip(s), QA, metadata tagging
2. **Media library + streaming app**: catalog, search, subscriptions, offline cache, workout planner
3. **Interactive 3D explorer**: separate realtime model linked into the catalog
4. Thin social / trainer assignment layer on top

If true, regenerating the product means:

- do **not** start by reverse-engineering their mp4s
- start by choosing a content generation architecture that can produce original exercise animations at acceptable cost/quality
- then wrap with a normal media+metadata product

## Success criteria for the research agent

A good research output answers:

1. What are the separable technical subsystems?
2. For the animation subsystem, what are the realistic generation methods in 2026?
3. What is the cheapest credible path to a *small* original library (say 20 exercises) that feels in-category?
4. What is the path to scale toward 200+ without a giant animation studio?
5. Which parts are commodity software vs hard IP?
6. What should we prototype first in this repo?
