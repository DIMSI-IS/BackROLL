const dayOfWeekMapping = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thrusday",
  "Friday",
  "Saturday",
  "Sunday",
];

export default {
  toSymbols(names) {
    let symbols = names.map((e) => dayOfWeekMapping.indexOf(e));
    if (names.includes("Sunday")) {
      symbols.push(0);
      symbols.push(7);
    }
    symbols = [...new Set(symbols)].sort();
    return symbols.length == dayOfWeekMapping.length ? ["*"] : symbols;
  },
  toNames(symbols) {
    return [
      ...new Set(
        symbols.includes("*")
          ? dayOfWeekMapping
          : symbols.map((e) => dayOfWeekMapping[e])
      ),
    ];
  },
};
