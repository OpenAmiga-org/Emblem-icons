/*
** memeater KB/N FILE: take all private memory (where programs' own
** allocations come from), then give back KB kilobytes of it, so other
** programs have only about that much left. Writes a status line to FILE,
** holds the memory until Ctrl-C, then gives it all back and appends to
** FILE (a low memory test for arcedit).
**
** On a big machine the private address space runs out before the memory
** does, so "AvailMem" says little; what's left is what memeater gave
** back. AmigaOS doesn't free AllocVec memory at exit, so the blocks are
** kept in a list (each block starts with the next one and its size).
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dos/dos.h>
#include <proto/exec.h>
#include <proto/dos.h>

struct block
{
 struct block *next;
 uint32 size;
};

static void report(const char *file, const char *text)
{
 BPTR fh = IDOS->Open(file, MODE_READWRITE);
 if(fh)
 {
  IDOS->ChangeFilePosition(fh, 0, OFFSET_END);
  IDOS->Write(fh, text, strlen(text));
  IDOS->Close(fh);
 }
}

int main(int argc, char **argv)
{
 uint32 keep = argc > 1 ? (uint32)atol(argv[1]) * 1024 : 1024 * 1024;
 const char *file = argc > 2 ? argv[2] : "RAM:memeater.txt";
 uint32 total = 0, back = 0, chunk = 16 * 1024 * 1024;
 struct block *list = NULL, *b;
 char line[160];

 /* everything, in smaller and smaller blocks */
 while(chunk >= 65536)
 {
  b = IExec->AllocVecTags(chunk, AVT_Type, MEMF_PRIVATE, AVT_Lock, FALSE, TAG_DONE);
  if(b == NULL)
  {
   chunk /= 2;
   continue;
  }
  b->next = list;
  b->size = chunk;
  list = b;
  total += chunk;
 }
 /* give back keep (the smallest blocks are at the front) */
 while(list && back < keep)
 {
  b = list;
  list = b->next;
  back += b->size;
  total -= b->size;
  IExec->FreeVec(b);
 }
 snprintf(line, sizeof(line), "memeater: holding %lu KB, gave back %lu KB, %lu KB free in all\n",
          (unsigned long)(total / 1024), (unsigned long)(back / 1024),
          (unsigned long)(IExec->AvailMem(MEMF_ANY) / 1024));
 report(file, line);
 IExec->Wait(SIGBREAKF_CTRL_C);
 while(list)
 {
  b = list;
  list = b->next;
  IExec->FreeVec(b);
 }
 report(file, "memeater: memory given back\n");
 return 0;
}
