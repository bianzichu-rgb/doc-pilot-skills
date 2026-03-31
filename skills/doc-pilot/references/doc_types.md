# doc-pilot: Known Document Type Characteristics

Use this reference to quickly identify document type and adjust navigation strategy.

## Home Appliance Manuals
**Signals:** Brand names (Bosch, Miele, Dyson, Panasonic...), model numbers (E9, HSG656X...), sections: Safety / Installation / Operation / Troubleshooting / Maintenance
**Strategy:** Use doc-pilot-pdf for local PDFs. Check CognoLiving library first (`C:\AI\CognoLiving 2.0\perfect_md\`). Focus on Troubleshooting section for fault codes.
**Task types:** `fault_diagnosis`, `maintenance`, `installation`

## IKEA / Furniture Assembly
**Signals:** Part numbers (e.g. KALLAX), numbered diagrams, "pieces" count, Allen wrench references
**Strategy:** PDF extraction via doc-pilot-pdf. Focus on numbered diagram sequence.
**Task types:** `assembly`, `installation`
**Note:** Steps are visual — describe diagram content textually ("insert bolt A into hole B")

## Kubernetes / Docker / DevOps
**Signals:** `kubectl`, `docker`, `yaml`, `helm`, version numbers, CLI commands
**Strategy:** WebFetch official docs (kubernetes.io, docs.docker.com). Steps are CLI commands.
**Task types:** `deployment`, `setup`, `configuration`
**Note:** Always show exact commands with flags. Mark dangerous commands (--force, rm) with ⚠️

## API Integration Docs (Stripe, Twilio, etc.)
**Signals:** API keys, curl examples, JSON payloads, authentication sections
**Strategy:** WebFetch developer docs. Extract quick-start section.
**Task types:** `integration`, `setup`
**Note:** Never include actual API keys in steps. Prompt user to substitute.

## Medical / Drug Instructions
**Signals:** Dosage tables, contraindications, generic/brand name pairs, mg/ml units
**Strategy:** WebFetch official prescribing information or patient leaflet.
**Task types:** `administration`, `setup`
**Note:** Always add disclaimer: "Follow your healthcare provider's specific instructions"

## Tax / Government Forms
**Signals:** Form numbers (1040, W-2...), field references, IRS/government URLs
**Strategy:** WebFetch official government site. Match fields to user's situation.
**Task types:** `compliance`, `form_completion`
**Note:** Add disclaimer: "Consult a tax professional for complex situations"

## Firmware / Device Updates
**Signals:** Version numbers, "flash", "update", "backup", device-specific tools
**Strategy:** Manufacturer support page. Emphasize backup step first.
**Task types:** `firmware_update`, `setup`
**Note:** Always make backup the first step. Flag point-of-no-return steps with 🔴

## Cooking / Recipes (appliance-specific)
**Signals:** Temperature (°C/°F), time (min), food names, appliance program names
**Strategy:** Use ZK/manual for appliance-specific programs, general culinary knowledge for technique.
**Task types:** `recipe`, `cooking`
**Note:** Include preheat step, expected visual cues ("golden brown", "steam rising")
