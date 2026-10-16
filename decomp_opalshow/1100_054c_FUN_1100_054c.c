
void __cdecl16far FUN_1100_054c(undefined2 param_1)

{
  byte bVar1;
  byte bVar2;
  undefined2 unaff_DS;
  
  FUN_1100_0762();
  bVar2 = (byte)param_1 | (byte)((uint)param_1 >> 8);
  LOCK();
  bVar1 = *(byte *)0x103a;
  *(byte *)0x103a = bVar2;
  UNLOCK();
  if ((bVar2 != 0) && (*(char *)0x1039 != '\0')) {
    *(undefined1 *)0x1039 = 0;
    *(int *)0x102f = *(int *)0x102f + 1;
    FUN_1100_06be(bVar1);
  }
  FUN_1100_077e();
  return;
}

