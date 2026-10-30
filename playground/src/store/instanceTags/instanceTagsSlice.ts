import type { PayloadAction } from "@reduxjs/toolkit";
import { createSlice } from "@reduxjs/toolkit";
import type { InstanceTagsResponse } from "@/api/types";
import { resetSchema, setOriginalSchema } from "@/store/schema/schemaSlice";
import type { RootState } from "@/store/types";

export interface InstanceTagsState {
	tagFields: InstanceTagsResponse;
	error: string | null;
}

const initialState: InstanceTagsState = {
	tagFields: {},
	error: null,
};

const instanceTagsSlice = createSlice({
	name: "instanceTags",
	initialState,
	reducers: {
		fetchInstanceTagsSuccess: (
			state,
			action: PayloadAction<InstanceTagsResponse>,
		) => {
			state.tagFields = action.payload;
			state.error = null;
		},
		fetchInstanceTagsFailure: (state, action: PayloadAction<string>) => {
			state.tagFields = {};
			state.error = action.payload;
		},
	},
	extraReducers: (builder) => {
		// The tag fields belong to the previous schema until the new ones load.
		builder.addCase(setOriginalSchema, () => initialState);
		builder.addCase(resetSchema, () => initialState);
	},
});

export const { fetchInstanceTagsSuccess, fetchInstanceTagsFailure } =
	instanceTagsSlice.actions;

export const selectInstanceTagFields = (state: RootState) =>
	state.instanceTags.tagFields;
export const selectInstanceTagsError = (state: RootState) =>
	state.instanceTags.error;

export default instanceTagsSlice.reducer;
