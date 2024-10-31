// TODO Understand why Sunday is 0 and 7.
const mapping = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thrusday",
  "Friday",
  "Saturday",
  "Sunday",
];

function week() {
  return [...Array(7).keys()].map((index) => mapping[index + 1]);
}

function toSymbols(names) {
  let symbols = names.map((e) => mapping.indexOf(e));
  if (names.includes("Sunday")) {
    symbols.push(0);
    symbols.push(7);
  }
  symbols = [...new Set(symbols)].sort();
  return symbols.length == mapping.length ? ["*"] : symbols;
}

function toNames(symbols) {
  return symbols.includes("*")
    ? week()
    : [...new Set(symbols.map((e) => (e == 0 ? 7 : e)))]
        .sort()
        .map((e) => mapping[e]);
}

export default {
  week,
  toSymbols,
  toNames,
};
