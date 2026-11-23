import { type LucideIcon, Monitor, Moon, Sun } from "lucide-react";
import { type ReactNode, useEffect, useLayoutEffect, useState } from "react";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { getIconClassName, isDarkTheme, type Theme } from "@/utils/theme";

const DARK_SCHEME_QUERY = "(prefers-color-scheme: dark)";

type ThemeOption = {
	value: Theme;
	label: string;
	Icon: LucideIcon;
};

const THEME_OPTIONS: ThemeOption[] = [
	{ value: "light", label: "Light", Icon: Sun },
	{ value: "dark", label: "Dark", Icon: Moon },
	{ value: "system", label: "System", Icon: Monitor },
];

export function ThemeToggle() {
	// Read during the first render, or a mount per workspace switch paints one
	// frame of the system theme. Guarded: a blocked accessor throws.
	const [theme, setTheme] = useState<Theme>(() => {
		try {
			return (localStorage.getItem("theme") as Theme | null) ?? "system";
		} catch {
			return "system";
		}
	});
	const [isDeviceDark, setIsDeviceDark] = useState(() => {
		const mediaQuery = window.matchMedia(DARK_SCHEME_QUERY);
		return mediaQuery.matches;
	});

	useEffect(() => {
		const mediaQuery = window.matchMedia(DARK_SCHEME_QUERY);
		const updateDeviceScheme = (event: MediaQueryListEvent) => {
			setIsDeviceDark(event.matches);
		};

		mediaQuery.addEventListener("change", updateDeviceScheme);
		return () => mediaQuery.removeEventListener("change", updateDeviceScheme);
	}, []);

	useLayoutEffect(() => {
		const isDark = isDarkTheme(theme, isDeviceDark);
		document.documentElement.classList.toggle("dark", isDark);
	}, [theme, isDeviceDark]);

	const handleThemeChange = (newTheme: Theme) => {
		setTheme(newTheme);
		try {
			localStorage.setItem("theme", newTheme);
		} catch {
			// Applies to this session, just not the next one.
		}
	};

	const selectedOption = THEME_OPTIONS.find((option) => option.value === theme);
	let selectedIcon: ReactNode = null;
	if (selectedOption) {
		const SelectedIcon = selectedOption.Icon;
		const selectedIconClassName = getIconClassName(theme, isDeviceDark);
		selectedIcon = <SelectedIcon className={selectedIconClassName} />;
	}

	return (
		<Select
			value={theme}
			onValueChange={(value) => handleThemeChange(value as Theme)}
		>
			<SelectTrigger aria-label={"Theme"} title={"Theme"}>
				<SelectValue>{selectedIcon}</SelectValue>
			</SelectTrigger>
			<SelectContent>
				{THEME_OPTIONS.map((option) => {
					const iconClassName = getIconClassName(option.value, isDeviceDark);
					return (
						<SelectItem key={option.value} value={option.value}>
							<div className={"flex items-center gap-2"}>
								<option.Icon className={iconClassName} />
								{option.label}
							</div>
						</SelectItem>
					);
				})}
			</SelectContent>
		</Select>
	);
}
