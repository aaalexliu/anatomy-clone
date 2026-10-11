# Agent prompt: research Muscle & Motion Strength core tech and regeneration paths

Copy everything below the line into a research agent.

---

## Mission

Research **Muscle & Motion Strength Training** (and closely related Muscle & Motion apps) to map the **core technological building blocks** behind the product, with special focus on the **3D exercise / muscle-in-motion videos** and the **interactive anatomy model**.

Then answer: **what is the best realistic way to regenerate a product in this category from first principles**, without copying Muscle & Motion’s proprietary assets?

This is category reverse-engineering and architecture research, not piracy.

## Non-negotiable constraints

- Do **not** dump, scrape, mirror, or redistribute Muscle & Motion videos, models, textures, or paid metadata.
- Do **not** propose training generative models on their proprietary clips to clone the look.
- Do **not** recommend DRM bypass, paywall circumvention, or binary cracking.
- You **may** use public pages, store listings, help docs, patents, job posts, vendor case studies, academic comps, and high-level observation of client behavior on a lawfully accessed account.
- Prefer original-generation and licensed-asset strategies.
- Mark every claim as **Observed / Inferred / Speculative** and cite sources.

## Starting context (seed, may be wrong)

Read `RESEARCH_BRIEF.md` in this repo if present. Condensed seed:

- Product value is visual biomechanics education: translucent 3D body doing exercises, muscle roles, joint actions, common mistakes, searchable anatomy model, 1200+ exercises.
- Public production story: expert brief -> animator -> multi-stage QA; some items take months.
- Platform story from a vendor case study: Flash/CD video library migrated to Netflix-like streaming; React / React Native / PHP / Mongo / Postgres / AWS / CDN.
- Android package ids still look Adobe AIR-era (`air.com.musclemotion.*`), which may be legacy naming only.
- System requirements talk like HD streamed animation/video + offline cache.
- Working hypothesis: hard moat is the **animation+taxonomy corpus**; app shell is commodity; interactive 3D model may be a second subsystem.

Your job is to confirm, correct, and deepen this.

## Research questions

### A. Product decomposition

Break the product into subsystems. For each, describe inputs, outputs, likely implementation class, and replaceability:

1. Exercise media (the “under the skin” animations)
2. Interactive 3D body explorer
3. Exercise knowledge graph / metadata (muscles, equipment, planes, cues, mistakes, alternatives)
4. Catalog search / filtering / recommendations
5. Workout builder + client assignment
6. Auth / subscription / payments / entitlements
7. Streaming / CDN / offline cache
8. CMS / internal publishing tools (if evidence exists)
9. Localization

Deliver a diagram-level architecture, not just a feature list.

### B. What exactly are the “videos”?

This is the central question. Determine, with evidence, which of these is true for Strength exercise demos:

- pre-rendered 2D video of 3D scenes (mp4/hls/dash)
- real-time 3D scenes in an engine (Unity/Unreal/three.js/native)
- hybrid: canned camera moves around realtime assets
- hybrid: video primary + separate realtime model elsewhere in the app
- something else

Investigate:

- web network behavior patterns (manifest names, cdn hosts, mime types) at architecture level
- mobile package / framework signals (AIR, RN, Unity, etc.) without publishing cracked internals
- whether playback supports arbitrary scrubbing, camera orbit during exercise playback, layer toggles, etc. (product UX is evidence)
- relationship between “exercise animation” and “3D model” screens

Output a decision tree: **if UX property X is present, infer architecture Y**.

### C. Content production system

Map the studio pipeline behind the media:

- DCC tools likely used
- shared base human / muscle rig vs one-off scenes
- hand keyframe vs mocap vs simulation vs procedural activation
- how muscle highlight / translucency / contraction is authored
- how “common mistake” variants are produced (separate clips vs layered)
- metadata authoring workflow
- cost/time per asset at small and large scale
- team composition implied by job posts / about pages / case studies

Find any patents, papers, talks, animator interviews, or job descriptions that reveal tooling.

### D. Regeneration options (original content only)

Propose **3–5 concrete regeneration strategies** for building an original library that occupies the same product category. Rank them on:

- visual quality ceiling
- biomechanical credibility
- cost per exercise
- time to first 20 exercises
- time to 200 exercises
- interactivity (camera, layers, muscle pick)
- engineering complexity
- legal cleanliness
- dependency risk (model vendors, talent, APIs)

Candidate families to evaluate (add/remove as evidence warrants):

1. **Classic animation studio clone-of-process**: Blender/Maya artists + shared anatomical rig + expert briefs + rendered video
2. **Realtime anatomical avatar product**: one high-quality body in Unity/Unreal/three.js; exercises as animation clips or animation graphs; muscle materials driven by weights/curves
3. **Mocap-to-anatomy**: capture real lifts (phone/IMU/optical), retarget to anatomical rig, author muscle activation curves semi-automatically, render or play realtime
4. **Simulation-assisted**: OpenSim / musculoskeletal models or physics-informed muscle activation, visualized on a mesh (research-heavy)
5. **AI-assisted acceleration**: use gen AI only as a force multiplier on *original* references, e.g. draft camera layouts, cleanup, texture helpers, metadata extraction from expert text — not as a ripper of M&M frames
6. **Licensed commercial anatomy engines** white-labeled or embedded, if any exist with exercise animation support
7. **Lower-fidelity wedge**: excellent 2D/SVG muscle maps + short real coach video + structured biomechanics text, only if you conclude full 3D is not the first wedge

For each strategy, name specific tools, model sources, open datasets, vendors, and example repos where possible.

### E. Data model

Design the minimum viable schema for:

- Muscle, origin/insertion, actions, innervation
- Joint, DOF, planes
- Exercise, equipment, setup, tempo
- Activation roles (agonist/synergist/stabilizer/antagonist) with confidence
- Clip/variant (correct form, mistake type)
- Cue / contraindication / regression / progression
- Media asset versions

Compare that schema to what the M&M UX appears to expose.

### F. Competitive and prior art scan

Compare architecture and content approach against:

- Complete Anatomy
- Visible Body
- AnatoFit and similar gym-anatomy startups
- PT/education animation libraries
- open exercise datasets / muscle map projects
- research musculoskeletal visualization tools

What did others do that M&M did not, and vice versa?

### G. Feasibility recommendation for this repo

End with a sharp recommendation:

1. **Do not build** / **prototype** / **full build** decision for an M&M-category product
2. The single best regeneration path for a solo/small team
3. A 2-week discovery prototype plan with acceptance checks
4. A 90-day plan to a demo with ~20 original exercises
5. Explicitly list what would still be weak vs M&M after that
6. Suggested first commits / folder structure for `anatomy-clone`

## Method

Work in this order:

1. Public product and docs pass
2. Store listing + package/framework signals
3. Vendor/case-study/job/patent pass
4. Competitor and open-source building-block pass
5. Architecture synthesis
6. Regeneration strategy matrix
7. Recommendation + prototype plan

Use the web. Prefer primary sources. When evidence conflicts, show the conflict.

If you can lawfully use a trial/subscription, do **observational** UX tests only:

- Can you orbit the camera during an exercise animation?
- Can you toggle muscles/bones live on the playing exercise?
- Is playback discrete clips or one continuous scene?
- Does offline mode download opaque media files vs engine bundles?
- How are mistakes presented: separate video, overlay, side-by-side?

Do not exfiltrate media bytes into the repo.

## Deliverables

Write these files into the working repo:

1. `docs/01-product-decomposition.md`
2. `docs/02-media-architecture-evidence.md` (claims + evidence table)
3. `docs/03-content-production-pipeline.md`
4. `docs/04-regeneration-strategy-matrix.md`
5. `docs/05-data-model-draft.md`
6. `docs/06-recommendation-and-prototype-plan.md`
7. `docs/sources.md` (links, dates accessed, notes)
8. Update `RESEARCH_BRIEF.md` with corrected conclusions

Also produce a short executive summary at the top of `docs/06-...` with:

- what M&M actually is, technically
- what is commodity
- what is hard
- best regeneration path
- first prototype

## Quality bar

- No handwavy “just use AI/Unity” answers
- Every major architectural claim needs evidence or is labeled speculative
- Cost/time estimates can be rough order-of-magnitude, but must state assumptions
- Separate **app clone difficulty** from **content corpus difficulty**
- Be opinionated in the final recommendation

## Definition of done

Research is done when a founder can answer yes/no to:

- “Are the exercise demos mostly streamed pre-renders or realtime 3D?”
- “Can a small team regenerate the *feeling* of the product with original assets?”
- “What exact pipeline should we pilot for the first 20 exercises?”
- “What should we build in week 1?”
