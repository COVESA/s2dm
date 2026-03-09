import { createSlice } from "@reduxjs/toolkit";

const appSlice = createSlice({
	name: "app",
	initialState: {},
	reducers: {
		appStartup: () => {},
		resetApp: () => {},
	},
});

export const { appStartup, resetApp } = appSlice.actions;

export default appSlice.reducer;
