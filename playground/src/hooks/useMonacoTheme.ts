import { useTheme } from "@/hooks/useTheme";

export function useMonacoTheme() {
	const theme = useTheme();
	if (theme === "dark") {
		return "vs-dark";
	}
	return "vs";
}
