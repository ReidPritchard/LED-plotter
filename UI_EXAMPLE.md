# UI Panel Example

## Before vs After

### Before (Original)
```
┌─ Vectorization Options ────────────────────┐
│                                             │
│ Render Style: [Stipples      ▼]            │
│                                             │
│ (No settings controls available)           │
│                                             │
└─────────────────────────────────────────────┘
```

### After (Enhanced)

**When Stipples is selected:**
```
┌─ Vectorization Options ────────────────────┐
│                                             │
│ Render Style: [Stipples      ▼]            │
│                                             │
│ ┌─ Style Settings ─────────────────────┐   │
│ │                                       │   │
│ │ Density:     [||||||||||||    ] 0.80 │   │
│ │                                       │   │
│ │ Max Radius:  [ 3.0  ] mm             │   │
│ │                                       │   │
│ │ Min Radius:  [ 0.5  ] mm             │   │
│ │                                       │   │
│ │ Points per Circle: [ 16   ]          │   │
│ │                                       │   │
│ │ ☑ Invert (dots in bright areas)      │   │
│ │                                       │   │
│ └───────────────────────────────────────┘   │
│                                             │
└─────────────────────────────────────────────┘
```

**When Hatching is selected:**
```
┌─ Vectorization Options ────────────────────┐
│                                             │
│ Render Style: [Hatching      ▼]            │
│                                             │
│ ┌─ Style Settings ─────────────────────┐   │
│ │                                       │   │
│ │ Line Spacing (Dark):  [ 2.0  ] mm    │   │
│ │                                       │   │
│ │ Line Spacing (Light): [ 10.0 ] mm    │   │
│ │                                       │   │
│ │ Angle: [||||||||||||        ] 45°    │   │
│ │         0°        90°       180°      │   │
│ │                                       │   │
│ │ Segment Max Length: [ 30.0 ] mm      │   │
│ │                                       │   │
│ │ Segment Min Length: [ 5.0  ] mm      │   │
│ │                                       │   │
│ │ Segment Gap:        [ 3.0  ] mm      │   │
│ │                                       │   │
│ └───────────────────────────────────────┘   │
│                                             │
└─────────────────────────────────────────────┘
```

## Usage Flow

### Example 1: Adjusting Stipple Rendering

```
User Action                          Result
────────────────────────────────────────────────────────────────
1. Select "Stipples"              → Stipple controls appear
2. Move density slider to 0.50    → Label shows "0.50"
                                    config.stipple_density = 0.50
3. Change max radius to 5.0       → config.stipple_max_radius = 5.0
4. Change min radius to 1.0       → config.stipple_min_radius = 1.0
5. Click "Process Image"          → Image rendered with new settings
                                    Result: Larger, sparser dots
```

### Example 2: Fine-tuning Hatching

```
User Action                          Result
────────────────────────────────────────────────────────────────
1. Select "Hatching"              → Hatching controls appear
2. Set dark spacing to 1.0 mm     → config.hatching_line_spacing_dark = 1.0
3. Set light spacing to 15.0 mm   → config.hatching_line_spacing_light = 15.0
4. Move angle slider to 90°       → Label shows "90°"
                                    config.hatching_angle = 90.0
5. Set segment max to 50.0 mm     → config.hatching_segment_max_length = 50.0
6. Set segment gap to 5.0 mm      → config.hatching_segment_gap = 5.0
7. Click "Process Image"          → Image rendered with new settings
                                    Result: Vertical hatching, long segments,
                                            dense in dark areas
```

### Example 3: Comparing Styles

```
Workflow: Creating two versions of same image
───────────────────────────────────────────────────────────────

Load image: rat-profile.jpg

Version 1: Dense Stipples
├─ Select "Stipples"
├─ Density: 0.90
├─ Max Radius: 2.0 mm
├─ Min Radius: 0.3 mm
├─ Process Image
└─ Add to Queue  → Commands saved

Version 2: Fine Hatching
├─ Select "Hatching"
├─ Dark Spacing: 1.5 mm
├─ Light Spacing: 8.0 mm
├─ Angle: 45°
├─ Segment Max: 20.0 mm
├─ Segment Min: 4.0 mm
├─ Segment Gap: 2.0 mm
├─ Process Image
└─ Add to Queue  → Commands saved

Result: Queue contains both versions, ready to plot
```

## Control Details

### Sliders (with live labels)

**Stipple Density:**
```
   0%                  50%                 100%
   │━━━━━━━━━━━━━━━━━╋━━━━━━━━━━━━━━━━━━│
                      ▲
                   Current: 0.80
                   Label updates as you drag
```

**Hatching Angle:**
```
   0°         45°        90°       135°     180°
   │━━━━━━━━━━╋━━━━━━━━━━╋━━━━━━━━━━╋━━━━━━│
             ▲
          Current: 45°
          Tick marks every 45°
          Label shows degrees symbol
```

### Spinboxes (with units)

**Max Radius:**
```
   ┌─────────────┐
   │  3.0    mm │  ← Unit shown as suffix
   │  ▲  ▼      │  ← Up/down arrows to adjust
   └─────────────┘

   Can type directly or use arrows
   Range: 0.1 to 10.0 mm
   Step: 0.5 mm
```

**Segment Gap:**
```
   ┌─────────────┐
   │  3.0    mm │
   │  ▲  ▼      │
   └─────────────┘

   Range: 0.5 to 20.0 mm
   Step: 0.5 mm
```

### Checkboxes

**Invert:**
```
   ☑ Invert (dots in bright areas)

   Unchecked (default): Dots in dark areas
   Checked: Dots in bright areas (negative effect)
```

## Tooltips

Hover over any control to see helpful tooltip:

```
   ┌─────────────────────────────────────┐
   │ Max Radius: [ 3.0  ] mm             │ ← Hover here
   └─────────────────────────────────────┘
            │
            ▼
   ┌──────────────────────────────────────┐
   │ Maximum dot radius in dark areas     │  ← Tooltip appears
   └──────────────────────────────────────┘
```

## Responsive Behavior

### Style Switching Animation

```
Time 0ms:  User clicks "Hatching" in dropdown
           │
           ▼
Time 10ms: render_style_combo emits currentIndexChanged(1)
           │
           ▼
Time 20ms: _on_render_style_changed(1) called
           ├─ Sets config.render_style = RenderStyle.HATCHING
           └─ Calls _update_style_controls(1)
                │
                ▼
Time 30ms: _update_style_controls(1) executes
           ├─ stipple_controls_widget.setVisible(False)
           └─ hatching_controls_widget.setVisible(True)
                │
                ▼
Time 40ms: Qt updates layout
           Stipple controls fade out
           Hatching controls fade in
           │
           ▼
Time 50ms: New layout complete
           User sees hatching controls
```

### Value Update Flow

```
User drags density slider
        │
        ▼
Slider emits valueChanged(75)
        │
        ▼
_update_stipple_density(75) called
        ├─ Calculates: density = 75 / 100.0 = 0.75
        ├─ Sets: config.stipple_density = 0.75
        └─ Updates: label.setText("0.75")
                │
                ▼
        Label shows "0.75" immediately
        Config ready for next processing
```

## Keyboard Shortcuts

**Spinboxes:**
- `↑` / `↓` - Increment/decrement by step
- `Page Up` / `Page Down` - Larger steps
- Type number directly, press Enter

**Sliders:**
- `←` / `→` - Fine adjustment
- `Page Up` / `Page Down` - Coarse adjustment
- Click to jump to position

**Checkboxes:**
- `Space` - Toggle when focused
- `Tab` - Navigate between controls

## Accessibility

- All controls have tooltips
- Keyboard navigation supported
- Clear visual hierarchy
- Consistent spacing and alignment
- Descriptive labels
- Units shown for all measurements

---

**End of UI Example**
