<template>
  <label class="simple-checkbox" :class="{ 'simple-checkbox--disabled': disabled, 'simple-checkbox--toggle': toggle }">
    <input type="checkbox" :checked="modelValue" :disabled="disabled" @change="onChange" />
    <span class="simple-checkbox__box" aria-hidden="true"><span class="simple-checkbox__mark" /></span>
    <span v-if="label" class="simple-checkbox__label">{{ label }}</span>
  </label>
</template>

<script>
// A checkbox, or a toggle with `toggle`, that does not depend on the one of the component library:
// with the version used here, that one does not display. Same use: v-model, label, disabled.
export default {
  name: "SimpleCheckbox",
  props: {
    modelValue: { type: Boolean, default: false },
    label: { type: String, default: "" },
    disabled: { type: Boolean, default: false },
    toggle: { type: Boolean, default: false },
  },
  emits: ["update:modelValue"],
  methods: {
    onChange(event) {
      this.$emit("update:modelValue", event.target.checked);
    },
  },
};
</script>

<style scoped>
.simple-checkbox {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  cursor: pointer;
  user-select: none;
  vertical-align: middle;
}

.simple-checkbox--disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.simple-checkbox input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

/* The box of a checkbox */
.simple-checkbox__box {
  position: relative;
  flex: 0 0 auto;
  width: 1.15rem;
  height: 1.15rem;
  border: 2px solid var(--va-primary);
  border-radius: 4px;
  background: transparent;
  transition: background 0.15s ease;
}

.simple-checkbox__mark {
  position: absolute;
  left: 0.28rem;
  top: 0.05rem;
  width: 0.28rem;
  height: 0.58rem;
  border: solid #fff;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg) scale(0);
  transition: transform 0.12s ease;
}

.simple-checkbox input:checked + .simple-checkbox__box {
  background: var(--va-primary);
}

.simple-checkbox input:checked + .simple-checkbox__box .simple-checkbox__mark {
  transform: rotate(45deg) scale(1);
}

.simple-checkbox input:focus-visible + .simple-checkbox__box {
  outline: 2px solid color-mix(in srgb, var(--va-primary) 45%, transparent);
  outline-offset: 2px;
}

/* The track and the knob of a toggle */
.simple-checkbox--toggle .simple-checkbox__box {
  width: 2.4rem;
  height: 1.3rem;
  border-radius: 1rem;
  border-color: color-mix(in srgb, var(--va-primary) 55%, #8a94a6);
  background: color-mix(in srgb, var(--va-primary) 22%, #cfd6e2);
}

.simple-checkbox--toggle .simple-checkbox__mark {
  left: 0.15rem;
  top: 0.15rem;
  width: 0.8rem;
  height: 0.8rem;
  border: 0;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.35);
  transform: none;
  transition: left 0.15s ease;
}

.simple-checkbox--toggle input:checked + .simple-checkbox__box {
  border-color: var(--va-primary);
  background: var(--va-primary);
}

.simple-checkbox--toggle input:checked + .simple-checkbox__box .simple-checkbox__mark {
  left: 1.2rem;
  transform: none;
}
</style>
