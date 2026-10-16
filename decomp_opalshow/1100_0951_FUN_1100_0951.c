
byte __cdecl16near FUN_1100_0951(undefined2 param_1,undefined2 param_2)

{
  byte bVar1;
  code *pcVar2;
  uint in_AX;
  undefined2 uVar3;
  char cVar5;
  uint uVar4;
  undefined2 unaff_SI;
  undefined2 unaff_DS;
  byte in_stack_00000000;
  
  if (*(char *)0x2d6 == '\x04') {
    if (in_AX < 0x10) {
      pcVar2 = (code *)swi(0x10);
      (*pcVar2)();
      return in_stack_00000000;
    }
  }
  else if ((*(char *)0x2d6 == '\x01') && (in_AX < 4)) {
    if ((*(byte *)0x1112 & 0x1c) != 0) {
      (*(code *)*(undefined2 *)0x2fb)();
      LOCK();
      bVar1 = *(byte *)0xffc;
      *(byte *)0xffc = (byte)unaff_SI;
      UNLOCK();
      return bVar1;
    }
    uVar3 = CONCAT11(uRam00000466,(char)in_AX);
    pcVar2 = (code *)swi(0x10);
    (*pcVar2)();
    pcVar2 = (code *)swi(0x10);
    (*pcVar2)(uVar3,unaff_SI);
    cVar5 = (char)((int)param_2 >> 0xc);
    uVar4 = CONCAT11(cVar5,cVar5) & 0xff01;
    uVar4 = CONCAT11((char)(uVar4 >> 8),(char)uVar4 << 1) & 0x2ff;
    return (byte)uVar4 | (byte)(uVar4 >> 9);
  }
  return 0xff;
}

