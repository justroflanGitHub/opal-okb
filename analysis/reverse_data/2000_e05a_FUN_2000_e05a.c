
void __stdcall16far FUN_2000_e05a(int *param_1,int *param_2)

{
  byte bVar1;
  char cVar2;
  int iVar3;
  undefined2 uVar4;
  undefined2 unaff_SI;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  long lVar5;
  char acStack_24 [16];
  int in_stack_0000ffec;
  int iStack_12;
  undefined1 auStack_8 [2];
  undefined2 uStack_6;
  undefined2 uStack_4;
  
  *(undefined2 *)0x5bd0 = *(undefined2 *)(*param_1 * 0x52 + 0x3528);
  *(int *)0x5bd4 = *(int *)(*param_1 * 0x52 + 0x352a) - *(int *)0x3840;
  *(undefined2 *)0x5bd2 = *(undefined2 *)(*param_1 * 0x52 + 0x352c);
  *(undefined2 *)0x5bd6 = *(undefined2 *)(*param_1 * 0x52 + 0x352e);
  uVar4 = *(undefined2 *)0x3148;
  *(undefined1 *)0x5bcc = *(undefined1 *)0x0;
  *(undefined1 *)0x5c09 = *(undefined1 *)0x1;
  *(undefined1 *)0x5c0a = *(undefined1 *)0x2;
  *(undefined1 *)0x5c08 = *(undefined1 *)0x3;
  func_0x00032028(0x1000,1,0x51 - *(int *)0x0,*(int *)0x0 + 1,0x54cc,0xc,0x875);
  iVar3 = FUN_3000_0458(0x2e73,0x882);
  *(int *)0x5c00 = iVar3;
  *(int *)0x5c02 = iVar3 >> 0xf;
  if (iVar3 != 0) {
    func_0x00032028(0x2e73,1,0x51 - *(int *)0xa4,*(int *)0xa4 + 0xa5,0x54cc,0xc,0x869);
    iVar3 = FUN_3000_0458(0x2e73,0x88e);
    *(int *)0x5c00 = iVar3;
    *(int *)0x5c02 = iVar3 >> 0xf;
  }
  if (*(int *)0x5c00 == 0 && *(int *)0x5c02 == 0) {
    FUN_3000_0772(0x2e73,0x89a);
    FUN_3000_0d22(0x2e73,0x8aa);
    *(undefined2 *)0x5bce = 1;
    do {
      iVar3 = *(int *)0x5bce;
      bVar1 = *(byte *)(iVar3 + 0x5bd7);
      *(uint *)0x5c0c = (uint)bVar1;
      if ((0x60 < bVar1) && (bVar1 < 0x7b)) {
        func_0x00032028(0x2e73,1,1,iVar3 + 0x5bd7);
      }
      *(int *)0x5bce = *(int *)0x5bce + 1;
    } while (*(int *)0x5bce < 0x3d);
    lVar5 = func_0x00032066(0x2e73,0,3,0x866);
    if (lVar5 != 0) {
      *(undefined2 *)0x5c06 = *(undefined2 *)0x3840;
      uVar4 = (undefined2)((ulong)param_1 >> 0x10);
      if ((((*param_1 == 0 && ((int *)param_1)[1] == 0) ||
           ((*param_1 == 1 && (((int *)param_1)[1] == 0)))) ||
          ((*param_1 == 3 && (((int *)param_1)[1] == 0)))) ||
         ((*param_1 == 4 && (((int *)param_1)[1] == 0)))) {
        *(undefined2 *)0x5c06 = 3;
      }
      *(int *)0x5bd0 = *(int *)(*param_1 * 0x52 + 0x3528) + *(int *)0x383e;
      *(int *)0x5bd4 = *(int *)(*param_1 * 0x52 + 0x352a) + *(int *)0x3840;
      *(int *)0x5bd2 = *(int *)(*param_1 * 0x52 + 0x352c) - *(int *)0x383e;
      *(int *)0x5bd6 = *(int *)(*param_1 * 0x52 + 0x352e) - *(int *)0x5c06;
    }
    uStack_6 = 0x28;
    uStack_4 = 4;
    *(int *)0x1944 = (int)auStack_8;
    *(undefined2 *)0x1946 = unaff_SS;
    iVar3 = FUN_2000_8388(0x5bd8);
    if (((iVar3 != 0) && (in_stack_0000ffec == 1)) && (iStack_12 == 0)) {
      *(undefined1 *)0x5c09 = 1;
    }
    uStack_6 = 0x28;
    uStack_4 = 5;
    *(int *)0x1944 = (int)auStack_8;
    *(undefined2 *)0x1946 = unaff_SS;
    iVar3 = FUN_2000_8388(0x5bd8);
    if (iVar3 != 0) {
      *(undefined1 *)0x5c0a = (char)in_stack_0000ffec;
    }
    uStack_6 = 0x28;
    uStack_4 = 6;
    *(int *)0x1944 = (int)auStack_8;
    *(undefined2 *)0x1946 = unaff_SS;
    iVar3 = FUN_2000_8388(0x5bd8);
    if (iVar3 != 0) {
      *(undefined1 *)0x5c08 = (char)in_stack_0000ffec;
    }
    lVar5 = func_0x00032066(0x2e73,0,3,0x851);
    if ((lVar5 != 0) && (lVar5 = func_0x00032066(0x2e73,0,5,0x84c), lVar5 == 0)) {
      *(undefined1 *)0x5bcc = 1;
      *(undefined1 *)0x5c0a = 0x4b;
    }
  }
  func_0x00032028(0x2e73,1,0x51 - *(int *)0xa4,*(int *)0xa4 + 0xa5,0x54cc,0xd,0x83f);
  func_0x00032028(0x2e73,1,0x51 - *(int *)0x52,*(int *)0x52 + 0x53,0x54cc,0xd,0x832);
  *(undefined2 *)0x5bce = 0;
  do {
    iVar3 = *(int *)0x5bce;
    cVar2 = *(char *)(iVar3 + 4);
    acStack_24[iVar3] = cVar2;
    if ((*(char *)0x5c09 == '\x01') && (cVar2 != '\0')) {
      acStack_24[iVar3] = '\x0f';
    }
    *(int *)0x5bce = *(int *)0x5bce + 1;
  } while (*(int *)0x5bce < 0x10);
  FUN_3000_0458(0x2e73,0x8ae);
  FUN_3000_0de2(0x8ba,0x1c,acStack_24,unaff_SS,unaff_SI);
  FUN_3000_0d22();
  if (*param_2 == 0 && ((int *)param_2)[1] == 0) {
    acStack_24[0xe] = '.';
    acStack_24[0xf] = '\b';
  }
  else {
    acStack_24[0xe] = -8;
    acStack_24[0xf] = '\0';
  }
  acStack_24[0xc] = -0x34;
  acStack_24[0xd] = 'T';
  acStack_24[10] = 'T';
  acStack_24[0xb] = '\0';
  acStack_24[8] = -0x34;
  acStack_24[9] = 'T';
  acStack_24[6] = -0x5a;
  acStack_24[7] = '\0';
  acStack_24[4] = -0x34;
  acStack_24[5] = 'T';
  acStack_24[2] = -0x5a;
  acStack_24[3] = '\0';
  acStack_24[0] = '\0';
  acStack_24[1] = '\0';
  uVar4 = FUN_3000_7c9c();
  *(undefined2 *)0x5c04 = uVar4;
  return;
}

