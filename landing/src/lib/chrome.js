import { createContext, useContext } from "react";

/**
 * Lets the full-screen guard hide the site chrome. The navbar sits outside
 * the routes, and the console is several levels inside one, so the two need
 * somewhere neutral to meet.
 */
export const ChromeContext = createContext({
  chromeHidden: false,
  setChromeHidden: () => {},
});

export const useChrome = () => useContext(ChromeContext);
