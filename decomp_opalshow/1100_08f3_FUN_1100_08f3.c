
undefined1 __cdecl16near FUN_1100_08f3(void)

{
  undefined1 uVar1;
  uint in_AX;
  byte bVar2;
  undefined2 unaff_DS;
  
  if ((char)(in_AX >> 8) == '\0') {
    bVar2 = *(byte *)0x2e1;
    if (*(char *)0x2d6 == '\0') {
      bVar2 = 0x1f;
    }
    if ((byte)in_AX <= bVar2) goto LAB_1100_090d;
  }
  in_AX = (uint)*(byte *)0x2e1;
LAB_1100_090d:
  LOCK();
  uVar1 = *(undefined1 *)0x1006;
  *(undefined1 *)0x1006 = (char)in_AX;
  UNLOCK();
  FUN_1100_0917();
  return uVar1;
}

