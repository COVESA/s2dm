import { useEffect, useState } from "react";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";

type Theme = "light" | "dark" | "system";

export function ThemeToggle() {
	const [theme, setTheme] = useState<Theme>("system");

	useEffect(() => {
		const stored = localStorage.getItem("theme") as Theme | null;
		setTheme(stored || "system");
	}, []);

	useEffect(() => {
		const root = document.documentElement;

		if (theme === "system") {
			const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

			const updateSystemTheme = (e: MediaQueryList | MediaQueryListEvent) => {
				if (e.matches) {
					root.classList.add("dark");
				} else {
					root.classList.remove("dark");
				}
			};

			updateSystemTheme(mediaQuery);
			mediaQuery.addEventListener("change", updateSystemTheme);

			return () => mediaQuery.removeEventListener("change", updateSystemTheme);
		} else if (theme === "dark") {
			root.classList.add("dark");
		} else {
			root.classList.remove("dark");
		}
	}, [theme]);

	const handleThemeChange = (newTheme: Theme) => {
		setTheme(newTheme);
		localStorage.setItem("theme", newTheme);
	};

	return (
		<Select
			value={theme}
			onValueChange={(value) => handleThemeChange(value as Theme)}
		>
			<SelectTrigger className="w-[130px]">
				<SelectValue />
			</SelectTrigger>
			<SelectContent>
				<SelectItem value="light">
					<div className="flex items-center">
						<span className="mr-2">☀️</span>
						Light
					</div>
				</SelectItem>
				<SelectItem value="dark">
					<div className="flex items-center">
						<span className="mr-2">🌙</span>
						Dark
					</div>
				</SelectItem>
				<SelectItem value="system">
					<div className="flex items-center">
						<span className="mr-2">💻</span>
						System
					</div>
				</SelectItem>
			</SelectContent>
		</Select>
	);
}
