/* iconload NAME... - load each icon with GetIconTags() and print the result,
 * the file format icon.library reports and the tool types. Spike helper. */
#include <proto/exec.h>
#include <proto/dos.h>
#include <proto/icon.h>
#include <workbench/icon.h>

int main(int argc, char **argv)
{
	struct Library *IconBase = IExec->OpenLibrary("icon.library", 51);
	struct IconIFace *IIcon = IconBase ? (struct IconIFace *)IExec->GetInterface(IconBase, "main", 1, NULL) : NULL;
	if (!IIcon) return 20;
	for (int i = 1; i < argc; i++)
	{
		STRPTR fmt = NULL;
		int32 err = 0;
		struct DiskObject *dobj = IIcon->GetIconTags(argv[i],
			ICONGETA_FailIfUnavailable, TRUE,
			ICONGETA_FileFormat, &fmt,
			ICONA_ErrorCode, &err, TAG_DONE);
		IDOS->Printf("%s: %p format '%s' err %ld\n", argv[i], dobj, fmt ? fmt : (STRPTR)"-", err);
		if (dobj)
		{
			uint32 w = 0, h = 0, f = 0;
			IIcon->IconControl(dobj, ICONCTRLA_GetWidth, &w, ICONCTRLA_GetHeight, &h,
				ICONCTRLA_GetImageDataFormat, &f, TAG_DONE);
			IDOS->Printf("  type %ld, %ldx%ld, image format %ld\n", (int32)dobj->do_Type, w, h, f);
			for (STRPTR *tt = dobj->do_ToolTypes; tt && *tt; tt++)
				IDOS->Printf("  tt: %s\n", *tt);
			IIcon->FreeDiskObject(dobj);
		}
	}
	IExec->DropInterface((struct Interface *)IIcon);
	IExec->CloseLibrary(IconBase);
	return 0;
}
