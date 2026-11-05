import { useColorMode } from "@docusaurus/theme-common";

// Docusaurus records the theme as `data-theme`, not a `dark` class.
export function useTheme(): "light" | "dark" {
	const { colorMode } = useColorMode();
	return colorMode === "dark" ? "dark" : "light";
}
