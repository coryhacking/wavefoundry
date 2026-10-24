Owner: Engineering
Status: active
Last verified: 2026-10-23

# Advisory Out-of-Scope Edit Sensor at Wave Review and Close

Agents sometimes edit files unrelated to the change they were asked to deliver, and the edits are easy to miss in a large wave diff. Every change document already declares the files it expects reviewers to look at under its `## Serialization Points` section, which serve as that change's review targets. Propose an advisory computational sensor that runs at Review wave and again at close. It collects the wave's git diff, unions the files declared under Serialization Points across all admitted changes, and lists every changed file that falls outside that union. The listing appears in the review readout as an informational section, names the changed path and the commit that touched it, and blocks nothing. Reviewers can then confirm each listed file belongs to the wave or send it back. Because it reuses declarations the planner already wrote, it needs no new authoring step and gives reviewers a cheap, mechanical signal for scope drift that today depends on someone noticing it by eye.

Source: the operator's one-line description of the sensor idea and the existing `## Serialization Points` convention in change docs. Deliberately left out: any observation about how Serialization Points entries are written in practice, any specific test file, and any mention of generated files.
