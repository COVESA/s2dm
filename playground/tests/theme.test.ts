import { expect, test } from "vitest";
import {
	getIconClassName,
	isDarkTheme,
	LIGHT_ICON_CLASS_NAME,
} from "@/utils/theme";

test("isDarkTheme keeps the light and dark themes whatever the device prefers", () => {
	const isLightDarkOnDarkDevice = isDarkTheme("light", true);
	const isDarkDarkOnLightDevice = isDarkTheme("dark", false);

	expect(isLightDarkOnDarkDevice).toBe(false);
	expect(isDarkDarkOnLightDevice).toBe(true);
});

test("isDarkTheme makes the system theme follow the device", () => {
	const isSystemDarkOnDarkDevice = isDarkTheme("system", true);
	const isSystemDarkOnLightDevice = isDarkTheme("system", false);

	expect(isSystemDarkOnDarkDevice).toBe(true);
	expect(isSystemDarkOnLightDevice).toBe(false);
});

test("getIconClassName colors the icon of a theme with the light look", () => {
	const lightClassNameOnDarkDevice = getIconClassName("light", true);
	const systemClassNameOnLightDevice = getIconClassName("system", false);

	expect(lightClassNameOnDarkDevice).toBe(LIGHT_ICON_CLASS_NAME);
	expect(systemClassNameOnLightDevice).toBe(LIGHT_ICON_CLASS_NAME);
});

test("getIconClassName keeps the default color for a theme with the dark look", () => {
	const darkClassNameOnLightDevice = getIconClassName("dark", false);
	const systemClassNameOnDarkDevice = getIconClassName("system", true);

	expect(darkClassNameOnLightDevice).toBeUndefined();
	expect(systemClassNameOnDarkDevice).toBeUndefined();
});
